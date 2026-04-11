from decimal import Decimal
from .Space import Vector3, Volume
from .Decimal import set_to_decimal

class Item:
    def __init__(self, name, volume : Volume, weight : Decimal, priority : int):
        """
        Item constructor
        
        :param self: Current Item object
        :param name: A name associated to the item
        :param volume: The space occupied by the item
        :type volume: Volume
        :param weight: Weight of the Item
        :param priority: Priority given to the Item
        """
        self.name   = name
        self._volume = volume
        self.weight = weight
        self.priority = priority

    @property
    def position(self):
        return self._volume.position
    @position.setter
    def position(self,value):
        self._volume.position = value

    @property
    def width(self):
        return self._volume.size.x
    @property
    def height(self):
        return self._volume.size.y
    @property
    def depth(self):
        return self._volume.size.z

    @property
    def volume(self):
        return self._volume

    @property
    def dimensions(self):
        return self._volume.size

    def __str__(self):
        return f"{self.name}({self.width}x{self.height}x{self.depth}, weight: {self.weight}) pos({self.position}) vol({self.volume.volume})"
    
    def format_numbers(self, number_of_decimals):
        self._volume.size.x = set_to_decimal(self.width, number_of_decimals)
        self._volume.size.y = set_to_decimal(self.height, number_of_decimals)
        self._volume.size.z = set_to_decimal(self.depth, number_of_decimals)
        self.weight = set_to_decimal(self.weight, number_of_decimals)

    def rotate90(self, orizontal : bool = False,vertical:bool=False):
        self._volume.rotate90(orizontal,vertical)