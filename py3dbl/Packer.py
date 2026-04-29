from decimal import Decimal
from .Item import Item
from .Bin import Bin, BinModel
from .Space import Vector3, Volume, rect_intersect
from .Decimal import decimals
from .Constraints import constraints, Constraint

# basical constraints 
BASE_CONSTRAINTS = [
    constraints['weight_within_limit'],
    constraints['fits_inside_bin'],
    constraints['central_corridor_accessibility'],
    constraints['no_overlap']
]

PACKING_STRATEGIES = ['greedy', 'multi_anchor']


def base_packer(available_bins : list[BinModel], items_to_pack : list[Item], default_bin : None|BinModel = None, constraints : list[Constraint] = BASE_CONSTRAINTS):
    
    def try_fit(bin : Bin, item : Item):
        old_pos = Vector3(*item.position)
        old_size = Vector3(*item.dimensions)
        
        for ib in bin.items:
            pivot = Vector3(*ib.position)
            for axis in range(3):
                # Set the item's position next to the current item along the specified axis
                new_pos = Vector3(*pivot)
                new_pos[axis] += ib.dimensions[axis]
                
                for oriz_deg_free in range(2):
                    for vert_deg_free in range(2):
                        # Set temporary X-Z position to compute surface heights
                        item.position = Vector3(new_pos.x, Decimal(0), new_pos.z)
                        
                        if axis == 1:
                            # Placing on top of pivot item: Y is fixed
                            y_candidates = [new_pos.y]
                        else:
                            # Placing along X or Z: find all valid resting surfaces
                            # by scanning items that overlap in X-Z at current rotation
                            y_set = set()
                            y_set.add(Decimal(0))  # floor is always an option
                            for existing in bin.items:
                                existing_top = existing.position.y + existing.height
                                overlap = rect_intersect(existing.volume, item.volume, 
                                                        Vector3.AXIS['x'], Vector3.AXIS['z'])
                                if overlap > 0:
                                    y_set.add(existing_top)
                            # Try highest surfaces first (prefer stacking)
                            y_candidates = sorted(y_set, reverse=True)
                        
                        for y_pos in y_candidates:
                            item.position = Vector3(new_pos.x, y_pos, new_pos.z)
                            if bin.put_item(item, constraints):
                                return True
                        
                        item.rotate90(vertical=True)
                    item.rotate90(orizontal=True)
        
        # Restore original position and dimensions if the item could not be placed
        item.position = old_pos
        item._volume.size = old_size
        return False

    current_configuration = []
    unfitted_items = []
    constraints.sort()

    while len(items_to_pack) != 0:
        if available_bins != None and len(available_bins) != 0:
            bin = Bin(len(current_configuration),available_bins.pop(0))
        elif default_bin != None:
            bin = Bin(len(current_configuration),default_bin)
        else:
            break

        # First pass: try to place each item
        retry_items = []  # Items that failed but might fit after others are placed
        for item in items_to_pack:
            if not bin.items:
                # First item in bin: try origin position
                if not bin.put_item(item, constraints):
                    retry_items.append(item)  # Retry later with try_fit
            else:
                if not try_fit(bin, item):
                    unfitted_items.append(item)
        
        # Second pass: retry items that failed when bin was empty
        # Now that other items might be placed, try_fit can find adjacent positions
        if bin.items and retry_items:
            for item in retry_items:
                if not try_fit(bin, item):
                    unfitted_items.append(item)
        else:
            # No items were placed, add retry_items to unfitted
            unfitted_items.extend(retry_items)

        # if no item has been packed probably there's no solution
        if len(bin.items) == 0:
            break

        items_to_pack = unfitted_items
        unfitted_items = []
        current_configuration.append(bin)
    
    # Return both configuration and any remaining unfitted items
    return current_configuration, items_to_pack


# ---------------------------------------------------------------------------
# Multi-Anchor Placement Strategy
# ---------------------------------------------------------------------------
# The greedy Left-Bottom-Back (LBB) heuristic accepts the *first* feasible
# position it finds for each item.  Because candidate positions are generated
# by iterating over already-placed items in insertion order, LBB has an
# inherent bias towards packing everything into the left-front-bottom corner
# of the bin.  When a Center-of-Gravity (CoG) constraint is active this bias
# causes many rejections and ultimately poor space utilisation.
#
# The multi-anchor strategy mitigates this by:
#   1. Generating candidate (x, z) positions from *multiple* anchor sources:
#        • Floor corners of the bin
#        • Geometric centre of the bin floor
#        • Item-adjacent positions (right / behind / diagonal / left / front)
#        • Wall-mirrored reflections of every anchor across X and Z centre
#          planes, so that both halves of the bin are explored equally
#   2. For each (x, z) anchor, computing all valid Y resting surfaces by
#      scanning items that overlap in the X-Z projection.
#   3. Evaluating *every* feasible (position × rotation) combination against
#      a lightweight scoring function that rewards:
#        • Low placement height                   (height_weight)
#        • Tight packing next to existing items    (compact_weight)
#      CoG balancing is NOT duplicated here: it is handled entirely by the
#      maintain_center_of_gravity constraint (if present), which filters
#      out invalid placements at step 3.  The multi-anchor's role is to
#      generate enough diverse candidates so the constraint can accept one.
#   4. Committing only the best-scoring placement for each item.
# ---------------------------------------------------------------------------

def multi_anchor_packer(available_bins: list[BinModel], items_to_pack: list[Item],
                        default_bin: None | BinModel = None,
                        constraints: list[Constraint] = BASE_CONSTRAINTS,
                        height_weight: float = 0.6,
                        compact_weight: float = 0.4):
    """
    Multi-anchor placement strategy for balanced 3D bin packing.

    Instead of accepting the first valid position (greedy LBB approach),
    generates candidate positions from multiple anchor points and selects
    the best placement for each item based on a scoring function that
    balances height and compactness.

    CoG balancing is handled entirely by the constraint system: if the
    ``maintain_center_of_gravity`` constraint is present in *constraints*,
    it will reject placements that push the centre of gravity too far
    from the bin centre.  The multi-anchor strategy generates enough
    diverse candidate positions so the constraint can find a valid one.

    :param available_bins: Ordered list of bin models to use (consumed by pop)
    :param items_to_pack: Items to pack (order may change across bins)
    :param default_bin: Fallback bin model when *available_bins* is exhausted
    :param constraints: Constraints every placement must satisfy
    :param height_weight: Scoring weight for height penalty (default 0.3)
    :param compact_weight: Scoring weight for compactness bonus (default 0.2)
    """

    # -- Anchor generation ---------------------------------------------------

    def _generate_xz_anchors(bin: Bin, item: Item) -> set[tuple[Decimal, Decimal]]:
        """
        Produce a set of (x, z) candidate positions from several anchor
        sources.  The returned coordinates represent the bottom-left-front
        corner of the item footprint.
        """
        anchors: set[tuple[Decimal, Decimal]] = set()
        iw = item.width
        idp = item.depth

        # Source 1 – Floor corners
        anchors.add((Decimal(0), Decimal(0)))
        rx = bin.width - iw
        bz = bin.depth - idp
        if rx >= 0:
            anchors.add((rx, Decimal(0)))
        if bz >= 0:
            anchors.add((Decimal(0), bz))
        if rx >= 0 and bz >= 0:
            anchors.add((rx, bz))

        # Source 2 – Bin centre (floor)
        cx = (bin.width - iw) / 2
        cz = (bin.depth - idp) / 2
        if cx >= 0 and cz >= 0:
            anchors.add((cx, cz))

        # Source 3 – Item-adjacent positions (limited to last 8 items for performance)
        for ib in bin.items[-8:]:
            px, pz = ib.position.x, ib.position.z
            # right of existing item
            anchors.add((px + ib.width, pz))
            # behind existing item
            anchors.add((px, pz + ib.depth))
            # diagonal (right-behind corner)
            anchors.add((px + ib.width, pz + ib.depth))
            # left of existing item (if space allows)
            left_x = px - iw
            if left_x >= 0:
                anchors.add((left_x, pz))
            # in front of existing item (if space allows)
            front_z = pz - idp
            if front_z >= 0:
                anchors.add((px, front_z))

        # Source 4 – Wall-mirrored reflections (balance across centre planes)
        snapshot = list(anchors)
        for (ax, az) in snapshot:
            mx = bin.width - iw - ax   # mirror across X centre
            mz = bin.depth - idp - az   # mirror across Z centre
            if mx >= 0:
                anchors.add((mx, az))
            if mz >= 0:
                anchors.add((ax, mz))
            if mx >= 0 and mz >= 0:
                anchors.add((mx, mz))

        # Filter: item must lie entirely inside the bin on the X-Z plane
        return {(x, z) for (x, z) in anchors
                if x >= 0 and z >= 0
                and x + iw <= bin.width and z + idp <= bin.depth}

    # -- Y-level scanner -----------------------------------------------------

    def _find_y_candidates(bin: Bin, item: Item,
                           x: Decimal, z: Decimal) -> list[Decimal]:
        """
        For a given (x, z) footprint, find all valid Y resting surfaces
        by scanning existing items.  Returns Y values sorted highest-first
        so that stacking (filling vertical gaps) is tried before the floor.
        """
        # Temporarily move item to (x, 0, z) so rect_intersect works
        item.position = Vector3(x, Decimal(0), z)
        y_set: set[Decimal] = {Decimal(0)}   # floor is always an option
        for existing in bin.items:
            existing_top = existing.position.y + existing.height
            # Only consider this surface if the item would fit vertically
            if existing_top + item.height <= bin.height:
                overlap = rect_intersect(existing.volume, item.volume,
                                         Vector3.AXIS['x'], Vector3.AXIS['z'])
                if overlap > 0:
                    y_set.add(existing_top)
        return sorted(y_set, reverse=True)

    # -- Placement scorer ----------------------------------------------------

    def _score_placement(bin: Bin, item: Item, pos: Vector3) -> float:
        """
        Score a candidate placement.  **Lower is better.**

        Components (all normalised to roughly [0, 1]):
          • Height penalty – prefer lower placements for stability.
          • Compactness    – prefer positions close to existing items to avoid
                             fragmentation.

        Note: CoG balancing is NOT performed here.  It is delegated entirely
        to the maintain_center_of_gravity constraint, which already filters
        out placements that violate the configured tolerances.
        """
        # --- Height penalty ---
        height_score = float(pos.y / bin.height) * height_weight

        # --- Compactness ---
        if bin.items:
            norm = float(bin.width + bin.height + bin.depth)
            min_dist = float('inf')
            for ib in bin.items:
                d = (float(abs(pos.x - ib.position.x))
                     + float(abs(pos.y - ib.position.y))
                     + float(abs(pos.z - ib.position.z)))
                if d < min_dist:
                    min_dist = d
            compact_score = (min_dist / norm) * compact_weight
        else:
            compact_score = 0.0

        return height_score + compact_score

    # -- Core placement routine ----------------------------------------------

    def _try_fit_multi_anchor(bin: Bin, item: Item) -> bool:
        """
        Attempt to place *item* inside *bin* by evaluating all candidate
        (anchor × y-level × rotation) combinations and committing only the
        placement with the lowest score.
        """
        old_pos  = Vector3(*item.position)
        old_size = Vector3(*item.dimensions)

        best_score: float = float('inf')
        best_pos:   Vector3 | None = None
        best_size:  Vector3 | None = None

        # Explore all 4 rotation variants (2 horizontal × 2 vertical)
        for _oriz in range(2):
            for _vert in range(2):
                xz_anchors = _generate_xz_anchors(bin, item)

                for (ax, az) in xz_anchors:
                    for y in _find_y_candidates(bin, item, ax, az):
                        item.position = Vector3(ax, y, az)

                        # Validate all constraints without committing
                        if all(c(bin, item) for c in constraints):
                            score = _score_placement(bin, item, item.position)
                            if score < best_score:
                                best_score = score
                                best_pos  = Vector3(*item.position)
                                best_size = Vector3(*item.dimensions)

                item.rotate90(vertical=True)
            item.rotate90(orizontal=True)
        # After the double loop the item is back to its original rotation.

        if best_pos is not None:
            assert best_size is not None  # always set together with best_pos
            item.position = best_pos
            item._volume.size = best_size
            # Commit – constraints were already satisfied during evaluation
            bin.items.append(item)
            bin.weight += item.weight
            return True

        # Restore original state when no valid placement was found
        item.position = old_pos
        item._volume.size = old_size
        return False

    # -- Main packing loop (same structure as base_packer) -------------------

    current_configuration: list[Bin] = []
    unfitted_items: list[Item] = []
    constraints = sorted(constraints)   # sort by weight without mutating input

    while len(items_to_pack) != 0:
        if available_bins is not None and len(available_bins) != 0:
            bin = Bin(len(current_configuration), available_bins.pop(0))
        elif default_bin is not None:
            bin = Bin(len(current_configuration), default_bin)
        else:
            break

        for item in items_to_pack:
            if not _try_fit_multi_anchor(bin, item):
                unfitted_items.append(item)

        # If no item was packed there is likely no feasible solution
        if len(bin.items) == 0:
            break

        items_to_pack = unfitted_items
        unfitted_items = []
        current_configuration.append(bin)

    # Return both configuration and any remaining unfitted items
    return current_configuration, items_to_pack

class Packer():
    """
    Store configurations and execute 3D bin packing algorithm(s)
    """
    def __init__(self, default_bin : None|BinModel = None, fleet : list[BinModel] | None = None, items : list[Item] | None = None, current_configuration : list[Bin] | None = None):
        """
        :param default_bin: a bin model that describes the preferred bin to pack in case the fleet is insufficent
        :type default_bin: None | BinModel
        :param bins: list of bin models that describes the fleet to pack
        :type bins: list[BinModel]
        :param items: list of items to fit in the fleet
        :type items: list[Item]
        :param current_configuration: a configuration to start on
        :type current_configuration: None | list[Bin]
        """
        self.bins   =  fleet if fleet is not None else []
        self.items  =  items if items is not None else []
        self.default_bin           = default_bin
        self.current_configuration = current_configuration if current_configuration is not None else []
        self.unfitted_items : list[Item] = []  # Items that could not be placed
    
    def set_default_bin(self, bin : BinModel):
        self.default_bin = bin
    
    def add_bin(self, bin : BinModel):
        self.bins.append(bin)

    def add_fleet(self, fleet : list[BinModel]):
        self.bins.extend(fleet)

    def add_batch(self, batch : list[Item]):
        self.items.extend(batch)

    def clear_current_configuration(self):
        self.current_configuration.clear()

    def _pack_to_bin(self, bin : Bin, item : Item, constraints):
        if not bin.items:
            return bin.put_item(item, constraints)
        else:
            for axis in range(0, 3):
                for ib in bin.items:
                    pivot = Vector3(*ib.position)
                    pivot[axis] += ib.dimensions[axis]
                    item.position = pivot
                    if bin.put_item(item, constraints):
                        return True
            return False

    def pack_test_on_models(self, models : list[BinModel], constraints : list[Constraint] = BASE_CONSTRAINTS):
        configuration = []
        for model in models:
            bin = Bin(0,model)
            for item in self.items:
                self._pack_to_bin(bin,item,constraints)
            configuration.append(bin)
        return configuration
    
    
    def pack(self, constraints : list[Constraint] = BASE_CONSTRAINTS, bigger_first=True, follow_priority=True, number_of_decimals=decimals, strategy='greedy',
             height_weight: float = 0.3, compact_weight: float = 0.2):
        """
        Execute the 3D bin packing on the given batch and fleet
        
        :param self: Current Packer object
        :param constraints: List of constraints to apply
        :param bigger_first: Sort items/bins by volume descending
        :param follow_priority: Respect item priorities (unused placeholder)
        :param number_of_decimals: Decimal precision for formatting
        :param strategy: Packing strategy to use: 'greedy' (Left-Bottom-Back) or
                         'multi_anchor' (balanced multi-anchor placement)
        :type strategy: str
        :param height_weight: (multi_anchor only) Scoring weight for placement height
        :param compact_weight: (multi_anchor only) Scoring weight for compactness
        """
        available_bins = self.bins
        items_to_pack = self.items

        for bin in available_bins:
            bin.format_numbers(number_of_decimals)

        for item in items_to_pack:
            item.format_numbers(number_of_decimals)

        if self.default_bin is not None:
            self.default_bin.format_numbers(number_of_decimals)
        
        available_bins.sort(
            key=lambda bin: bin.volume, reverse=bigger_first
        )
        items_to_pack.sort(
            # (NEW) SORTING SECONDO PRIORITÀ CRESCENTE, A PARITÀ DELLA STESSA, PESO DECRESCENTE
            key=lambda item: (item.priority, item.volume.volume())
        )


        if strategy == 'multi_anchor':
            self.current_configuration, self.unfitted_items = multi_anchor_packer(
                available_bins=available_bins,
                items_to_pack=items_to_pack,
                default_bin=self.default_bin,
                constraints=constraints,
                height_weight=height_weight,
                compact_weight=compact_weight,
            )
        else:
            self.current_configuration, self.unfitted_items = base_packer(
                available_bins=available_bins,
                items_to_pack=items_to_pack,
                default_bin=self.default_bin,
                constraints=constraints,
            )
        """
        unfitted_items = []
        static_constraints, space_constraints = process_constraints(constraints)

        while len(items_to_pack) != 0:
            if available_bins != None and len(available_bins) != 0:
                bin = available_bins.pop(0)
            elif self.default_bin != None:
                bin = Bin(len(self.current_configuration),self.default_bin)
            else:
                return

            for item in items_to_pack:
               if not self._pack_to_bin(bin,item,static_constraints=static_constraints.copy(),space_constraints=space_constraints.copy()):
                   unfitted_items.append(item)

            if len(bin.items) == 0:
                break

            items_to_pack = unfitted_items
            unfitted_items = []
            self.current_configuration.append(bin)
        return len(items_to_pack)"""

    def calculate_statistics(self):
        statistics = {
            "loaded_volume": Decimal(0),
            "loaded_weight": Decimal(0),
        }
        configuration_volume = Decimal(0)
        for bin in self.current_configuration:
            for item in bin.items:
                statistics["loaded_volume"] += item.volume.volume()
            statistics["loaded_weight"] += bin.weight
            configuration_volume += bin._model.volume
        
        # Evita divisione per zero
        if configuration_volume > 0:
            statistics["average_volume"] = statistics["loaded_volume"]/configuration_volume
        else:
            statistics["average_volume"] = Decimal(0)
        
        return statistics

# ============================================================================
# Funzione di analisi: Conta per ogni pacco, secondo la sua priorità, 
# il numero di mosse che l'operatore deve fare per poterlo estrarre.
# ============================================================================

def calculate_moves_v5(bin_obj: Bin, has_corridor: bool, CORRIDOR_WIDTH_PCT):
    items = bin_obj.items
    bw, bd = float(bin_obj.width), float(bin_obj.depth)
    c_half = (bw * CORRIDOR_WIDTH_PCT) / 2
    c_min, c_max = (bw / 2) - c_half, (bw / 2) + c_half
    priorities = sorted(list(set(int(i.priority) for i in items)), reverse=True)
    unloading_results = {}

    def get_all_blockers(target, current_context, memo, visited):
        if target.name in memo: return memo[target.name]
        if target.name in visited: return set()
        visited.add(target.name)
        tx, ty, tz = float(target.position.x), float(target.position.y), float(target.position.z)
        tw, th, td = float(target.width), float(target.height), float(target.depth)

        top_blockers = set()
        for other in current_context:
            if (other.name == target.name or other.priority == target.priority): continue
            ox, oy, oz = float(other.position.x), float(other.position.y), float(other.position.z)
            ow, oh, od = float(other.width), float(other.height), float(other.depth)
            if oy >= (ty + th - 0.005):
                if not (tx + tw <= ox + 0.005 or tx >= ox + ow - 0.005 or tz + td <= oz + 0.005 or tz >= oz + od - 0.005):
                    top_blockers.add(other.name)
                    top_blockers.update(get_all_blockers(other, current_context, memo, visited))

        rear_path = set()
        for other in current_context:
            if (other.name == target.name or other.priority == target.priority): continue
            ox, oy, oz = float(other.position.x), float(other.position.y), float(other.position.z)
            ow, oh, od = float(other.width), float(other.height), float(other.depth)
            if oz >= (tz + td - 0.005):
                if not (tx + tw <= ox + 0.005 or tx >= ox + ow - 0.005 or ty + th <= oy + 0.005 or ty >= oy + oh - 0.005):
                    rear_path.add(other.name)
                    rear_path.update(get_all_blockers(other, current_context, memo, visited))

        corridor_path = set()
        can_use_corr = False
        if has_corridor:
            is_left = (tx + tw/2) < (bw/2)
            if (is_left and abs(tx + tw - c_min) < 0.03) or (not is_left and abs(tx - c_max) < 0.03): can_use_corr = True
            else:
                for other in current_context:
                    if (other.name == target.name or other.priority == target.priority): continue
                    ox, oy, oz = float(other.position.x), float(other.position.y), float(other.position.z)
                    ow, oh, od = float(other.width), float(other.height), float(other.depth)
                    overlap_yz = not (ty + th <= oy + 0.005 or ty >= oy + oh - 0.005 or tz + td <= oz + 0.005 or tz >= oz + od - 0.005)
                    if is_left and (ox >= tx + tw - 0.005 and ox < c_min) and overlap_yz:
                        corridor_path.add(other.name); corridor_path.update(get_all_blockers(other, current_context, memo, visited))
                    elif not is_left and (ox + ow <= tx + 0.005 and ox + ow > c_max) and overlap_yz:
                        corridor_path.add(other.name); corridor_path.update(get_all_blockers(other, current_context, memo, visited))
                can_use_corr = True

        horizontal = corridor_path if (can_use_corr and len(corridor_path) < len(rear_path)) else rear_path
        total = top_blockers.union(horizontal)
        memo[target.name] = total
        visited.remove(target.name)
        return total

    for cp in priorities:
        remaining_now = [i for i in items if int(i.priority) <= cp]
        targets_now = [i for i in remaining_now if int(i.priority) == cp]
        memo_at_stop = {}
        for T in targets_now:
            unloading_results[T.name] = len(get_all_blockers(T, remaining_now, memo_at_stop, set()))
    return unloading_results
