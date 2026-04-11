from decimal import Decimal
from typing import Union
from .Decimal import set_to_decimal
from .Item import Item
from .Space import Vector3

MINIMUM_SUPPORT_SURFACE = .5

class BinModel:
    """
    Describes a model of bin
    """
    def __init__(self, name : str, size : Union[Vector3, tuple], max_weight : Union[Decimal, int, float]):
        """
        BinModel constructor
        
        :param self: Current BinModel object
        :param name: A descriptive name for the model
        :type name: str
        :param size: 3D vector that defines the sizes of the Bin (can also be a tuple)
        :type size: Vector3 | tuple
        :param max_weight: Maximum weight allowed to load
        :type max_weight: Decimal | int | float
        """
        self.name = name
        self._size = Vector3(*size) if not isinstance(size, Vector3) else size
        self.max_weight = Decimal(max_weight) if not isinstance(max_weight, Decimal) else max_weight

    # Properties to simplify access
    # Note: sizes are only defined on construction
    @property
    def width(self):  return self._size.x
    @width.setter
    def width(self,value):  self._size.x = value

    @property
    def height(self): return self._size.y
    @height.setter
    def height(self,value): self._size.y = value

    @property
    def depth(self):  return self._size.z
    @depth.setter
    def depth(self,value):  self._size.z = value

    @property
    def dimension(self): return self._size

    @property
    def volume(self):    return self.width * self.height * self.depth
    
    def __str__(self):
        return "%s(%sx%sx%s, max_weight:%s) vol(%s)" % (
            self.name, self.width, self.height, self.depth, self.max_weight,
            self.volume
        )
    
    def format_numbers(self, number_of_decimals):
        self.width = set_to_decimal(self.width, number_of_decimals)
        self.height = set_to_decimal(self.height, number_of_decimals)
        self.depth = set_to_decimal(self.depth, number_of_decimals)
        self.max_weight = set_to_decimal(self.max_weight, number_of_decimals)


class Bin:
    """
    Describes a loadable bin (i.e. an instance of a bin)
    """
    def __init__(self, id, model : BinModel):
        """
        Bin constructor
        
        :param self: Current Bin object
        :param id: identifier (no uniqueness constraint)
        :param model: Reference model
        :type model: BinModel
        """
        self.id = id
        self._model : BinModel   = model
        self.weight : Decimal    = Decimal(0)   # Current loaded weight
        self.items  : list[Item] = []  # Current loaded items

    # Properties to access model data
    # Note: direct write access is not allowed
    @property
    def width(self):
        return self._model.width
    @property
    def height(self):
        return self._model.height
    @property
    def depth(self):
        return self._model.depth
    @property
    def dimension(self):
        return self._model.dimension
    @property
    def max_weight(self):
        return self._model.max_weight

    def __str__(self):
        return f"Bin {self.id} of model {self._model.name}: loaded items {len(self.items)}"

    def put_item(self, item : Item, constraints = []):
        """
        Insert an item in the bin
        
        :param item: Item to insert
        :type item: Item
        :param pivot: Starting position of the item
        :type pivot: Vector3
        :param constraints: List of constraints (see .Constraints) to follow
        :type static_constraints: list[Constraint]
        """
        if all([c(self,item) for c in constraints]):
            self.items.append(item)
            self.weight += item.weight
            return True
        else:
            return False
    
    def remove_item(self, item : Item):
        try:
            self.items.remove(item)
            self.weight -= item.weight
            return True
        except ValueError:
            return False # the item was not there

    def calculate_center_of_gravity(self):
        """"
        Calculate the center of gravity of the current load in the bin.
        Returns a Vector3 representing the center of gravity coordinates (x, y, z).
        """
        total_weight = self.weight

        if total_weight == 0:
            return Vector3(self.width / 2, self.height / 2, self.depth / 2)  # Center of the bin if empty
        
        moment_x = Decimal(0);
        moment_y = Decimal(0);
        moment_z = Decimal(0);  

        for item in self.items:
            # Calculate the center of gravity of the item
            # The item position is the coordinate of its bottom-left-front corner, so we add half of its dimensions 
            # to get the center of the item
            center_x = item.position.x + (item.width / Decimal(2))
            center_y = item.position.y + (item.height / Decimal(2))
            center_z = item.position.z + (item.depth / Decimal(2))

            # Sum of the moments (Lever arm * Weight )
            moment_x += center_x * item.weight
            moment_y += center_y * item.weight
            moment_z += center_z * item.weight


        cog_x = moment_x / total_weight
        cog_y = moment_y / total_weight
        cog_z = moment_z / total_weight

        return Vector3(cog_x, cog_y, cog_z)