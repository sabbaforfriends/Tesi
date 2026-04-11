from .Bin import Bin
from .Item import Item
from .Space import Volume, Vector3, intersect, rect_intersect
from decimal import Decimal

class Constraint:
    """
    A Constraint to apply to a bin packing problem
    """
    def __init__(self,func ,weight : int = 0):
        """
        :param func: Function that evaluates the constraint
        :param weight: Weight used for evaluation order (generally more expensive constraint should have higher weight)
        :type weight: int
        :param type: A Type used to distinguish between constraints: STATIC a constraint that depends on statical properties of the bin and the item, SPACE_DEPENDENT a constraint that depends on the position of the item
        :type type: ConstraintType
        """
        self.func = func
        self.weight = weight
        self.kwargs = dict()
    
    def set_parameter(self,name : str, value):
        """
        Set parameter different from the bin and the item
        
        :param name: Name of the parameter
        :type name: str
        :param value: Value to set
        """
        self.kwargs[name] = value

    # used for ordering
    def __lt__(self,cmp):
        return self.weight < cmp.weight
    def __call__(self, bin : Bin, item : Item):
        return self.func(bin,item,**self.kwargs)
    def __str__(self):
        return f"Constraint {self.func.__name__} weight({self.weight})"

# dictionary of currently available constraints
constraints = dict()

def constraint(weight : int):
    """
    Decorator for simple Constraint generation
    
    :param weight: Weight of the constraint
    :type weight: int
    """
    def wrapper(func):
        constraints[func.__name__] = Constraint(func,weight)
        return func
    return wrapper

# Ready-Made Constraint

@constraint(weight=5)
def weight_within_limit(bin : Bin, item : Item):
    return bin.weight+item.weight <= bin.max_weight

@constraint(weight=10)
def fits_inside_bin(bin : Bin, item : Item):
    return all([bin.dimension[axis] >= (item.position[axis] + item.dimensions[axis]) for axis in range(3)])
    
@constraint(weight=15)
def no_overlap(bin : Bin, item : Item):
    return len(bin.items) == 0 or not any([intersect(ib.volume,item.volume) for ib in bin.items])

@constraint(weight=20)
def is_supported(bin: Bin, item : Item, minimum_support : float = 0.50): #cambiato per prova, inizialmente era 0.75
    """
    Check that the item is physically supported by direct contact.
    Only counts support from items whose top surface is exactly at the item's bottom Y.
    This is a pure validator: it does NOT modify the item's position.
    
    :param minimum_support: Minimum ratio of the item's base area that must be supported (0.0-1.0)
    :type minimum_support: float
    """
    # Items on the floor are always supported
    if item.position.y == 0:
        return True
    
    # Base area of the item (X-Z plane)
    item_base_area = item.dimensions[Vector3.AXIS['x']] * item.dimensions[Vector3.AXIS['z']]
    if item_base_area <= 0:
        return False
    
    # Only count support from items in direct contact:
    # their top surface must be exactly at the item's bottom Y
    contact_area = Decimal(0)
    for ib in bin.items:
        ib_top_y = ib.position.y + ib.height
        if ib_top_y == item.position.y:
            overlap = rect_intersect(ib.volume, item.volume, Vector3.AXIS['x'], Vector3.AXIS['z'])
            if overlap > 0:
                contact_area += overlap
    
    support_ratio = contact_area / item_base_area
    return support_ratio >= Decimal(str(minimum_support))

@constraint(weight=25) 
def maintain_center_of_gravity(bin : Bin, item : Item, 
                              tol_x_percent : float = 0.10,
                              tol_z_percent : float = 0.10,
                              progressive_tightening : float = 0.7):
    """
    Progressive Center-of-Gravity constraint.

    Checks that the CoG of the bin after placing the item stays within a
    tolerance zone around the bin centre on the X-Z plane.

    The constraint becomes **progressively stricter** as the bin fills up:
    at low load ratios the tolerance is at its configured maximum, and it
    shrinks linearly towards ``tol * (1 - progressive_tightening)`` when
    the bin is fully loaded.  This gives early items freedom to spread out
    while forcing later items to correct any imbalance.

    Additionally, a **corrective bias** is applied: when the current CoG
    deviates from the bin centre by more than half the effective tolerance,
    any placement that would *increase* that deviation is rejected.  This
    prevents the imbalance from growing once it becomes significant.

    :param tol_x_percent: Maximum tolerance on X as a ratio of bin width (0.0-1.0)
    :param tol_z_percent: Maximum tolerance on Z as a ratio of bin depth (0.0-1.0)
    :param progressive_tightening: How much the tolerance shrinks at full load (0.0-1.0).
           0.0 = fixed tolerance, 1.0 = tolerance shrinks to zero at full load.
    """
    
    # Calculate the future weight and load ratio
    future_weight = bin.weight + item.weight
    if bin.max_weight > 0:
        load_ratio = future_weight / bin.max_weight
    else:
        load_ratio = Decimal(0)
        
    # Calculate the current center of gravity
    current_cog = bin.calculate_center_of_gravity()

    # Calculate the total moment of the current load
    current_moment_x = current_cog.x * bin.weight
    current_moment_z = current_cog.z * bin.weight

    # Calculate the moments of the new item
    item_center_x = item.position.x + (item.width / Decimal(2))
    item_center_z = item.position.z + (item.depth / Decimal(2))

    item_moment_x = item_center_x * item.weight
    item_moment_z = item_center_z * item.weight

    # Calculate the future center of gravity
    future_cog_x = (current_moment_x + item_moment_x) / future_weight
    future_cog_z = (current_moment_z + item_moment_z) / future_weight

    # Reference centre of the bin (Z shifted towards the back for vehicle stability)
    bin_center_x = bin.width / Decimal(2)
    bin_center_z = bin.depth / Decimal(2) 

    # Progressive tolerance: shrinks linearly with load_ratio
    #   load_ratio ≈ 0  →  effective_tol = tol_max  (full freedom)
    #   load_ratio = 1  →  effective_tol = tol_max * (1 - progressive_tightening)
    tightening = Decimal(str(progressive_tightening))
    scale = Decimal(1) - (load_ratio * tightening)
    tol_x = bin.width * Decimal(str(tol_x_percent)) * scale
    tol_z = bin.depth * Decimal(str(tol_z_percent)) * scale

    # Future deviations from bin centre
    future_dev_x = abs(future_cog_x - bin_center_x)
    future_dev_z = abs(future_cog_z - bin_center_z)

    # Hard reject: future CoG outside the progressive tolerance zone
    if future_dev_x > tol_x:
        return False
    if future_dev_z > tol_z:
        return False

    # Corrective bias: if the current CoG is already significantly off-centre,
    # reject placements that would make it worse.
    if bin.weight > 0:
        current_dev_x = abs(current_cog.x - bin_center_x)
        current_dev_z = abs(current_cog.z - bin_center_z)

        # Threshold = half the effective tolerance
        if current_dev_x > tol_x / 2 and future_dev_x > current_dev_x:
            return False
        if current_dev_z > tol_z / 2 and future_dev_z > current_dev_z:
            return False

    return True  


@constraint(weight=21)
def central_corridor_accessibility(bin: Bin, item: Item, 
                                 corridor_width_percent: float = 0.2,
                                 corridor_depth_percent: float = 0.85):
    """
    Centered aisle, created in order to reduce items movements and to make worker access easier
    
    :param corridor_width_percent: Percentage of total width dedicated to the aisle (es. 0.2 = 20%)
    :param corridor_depth_percent: Percentage of total depth dedicated to the aisle (es. 0.85 = 85%)
    """
    
    # Calculating aisle x limits
    half_width_pct = Decimal(str(corridor_width_percent)) / 2
    bin_center_x = bin.width / 2
    
    # Calculating aisle z limits
    corridor_z_max = bin.depth * (1 - Decimal(str(corridor_depth_percent)))

    corridor_x_min = bin_center_x - (bin.width * half_width_pct)
    corridor_x_max = bin_center_x + (bin.width * half_width_pct)

    # Item position
    item_x_min = item.position.x
    item_x_max = item.position.x + item.width
    item_z_min = item.position.z + item.depth

    # Verifying intersections
    intersects_x = not (item_x_max <= corridor_x_min or item_x_min >= corridor_x_max)
    intersects_z = (item_z_min >= corridor_z_max)
    
    if (intersects_x and intersects_z):
        return False # Collision detected

    return True