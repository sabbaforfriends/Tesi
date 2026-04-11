from decimal import Decimal
import functools as tools

class Vector3:
    """
    A point in a 3D space

    Note: keep an eye on object assignment (which is by reference) and argument packing/unpacking in constructors
    """
    AXIS = { "x": 0, "y": 1, "z": 2}

    def __init__(self, x : Decimal = Decimal(0), y : Decimal = Decimal(0), z : Decimal = Decimal(0)):
        self.vect = [x,y,z]

    @property
    def x(self):
        return self.vect[self.AXIS["x"]]
    @property
    def y(self):
        return self.vect[self.AXIS["y"]]
    @property
    def z(self):
        return self.vect[self.AXIS["z"]]
    @x.setter
    def x(self,value):
        self.vect[self.AXIS["x"]] = value
    @y.setter
    def y(self,value):
        self.vect[self.AXIS["y"]] = value
    @z.setter
    def z(self,value):
        self.vect[self.AXIS["z"]] = value

    def __len__(self):
        return 3
    
    def __getitem__(self,idx : int):
        return self.vect[idx]
    
    def __setitem__(self,idx : int, value : Decimal):
        self.vect[idx] = value
    
    def __str__(self):
        return f"x:{self.x},y:{self.y},z:{self.z}"
    
    def __add__(self,target):
        y = Vector3(*target)
        y.x += self.x
        y.y += self.y
        y.z += self.z
        return y

    def rotate90(self, orizontal : bool = False, vertical : bool = False):
        """
        Rotate of 90 degrees in orizontal or vertical
        
        :param self: Current Vector3 object
        :param orizontal: True to make a orizontal rotation (i.e. width-depth)
        :type orizontal: bool
        :param vertical: True to make a vertical rotation (i.e. height-depth)
        :type vertical: bool
        """
        if orizontal:
            self.vect[0], self.vect[2] = self.vect[2], self.vect[0]
        if vertical:
            self.vect[1], self.vect[2] = self.vect[2], self.vect[1]

class Volume:
    """
    Models an occupied space
    """

    def __init__(self, size : Vector3, position : Vector3 | None = None):
        """
        Constructor for Volume object
        
        :param self: Current Volume object
        :param size: 3D Vector that describes the size of the occupied space
        :type size: Vector3
        :param position: 3D Vector that describes the central point 
        :type position: Vector3
        """
        if position is None:
            position = Vector3()
        self.position = Vector3(*position)
        self.size = Vector3(*size)

    def volume(self):
        """
        Volumetric occupation
        
        :param self: Current Volume object
        """
        toReduce = self.size.vect
        return tools.reduce(lambda x,y: x*y, toReduce, 1)

    def rotate90(self, orizontal : bool = False, vertical : bool = False):
        """
        Rotate of 90 degrees in orizontal or vertical
        
        :param self: Current Volume object
        :param orizontal: True to make a orizontal rotation (i.e. width-depth)
        :type orizontal: bool
        :param vertical: True to make a vertical rotation (i.e. height-depth)
        :type vertical: bool
        """
        self.size.rotate90(orizontal,vertical)

def rect_intersect(item1 : Volume, item2 : Volume, x : int, y : int):
    """
    Check for 2D intersection on the plane formed by the given axis (x,y)
    
    :param item1: First 3D object (intersected)
    :type item1: Volume
    :param item2: Second 3D object (intersector)
    :type item2: Volume
    :param x: First axis
    :type x: int
    :param y: Second axis
    :type y: int
    """
    d1 = item1.size # sizes of 1
    d2 = item2.size # sizes of 2

    cx1 = item1.position[x] + d1[x]/2 # center of 1 on axis x
    cy1 = item1.position[y] + d1[y]/2 # center of 1 on axis y
    cx2 = item2.position[x] + d2[x]/2 # center of 2 on axis x
    cy2 = item2.position[y] + d2[y]/2 # center of 2 on axis y

    # distance between the centers
    ix = abs(cx2 - cx1)
    iy = abs(cy2 - cy1)

    overlap_x = max(0,(d1[x]+d2[x])/2 - ix)
    overlap_y = max(0,(d1[y]+d2[y])/2 - iy)

    return abs((overlap_x) * (overlap_y)) # overlap area


def intersect(item1 : Volume, item2 : Volume):
    return (
        rect_intersect(item1, item2, Vector3.AXIS["x"], Vector3.AXIS["y"])!=0 and
        rect_intersect(item1, item2, Vector3.AXIS["y"], Vector3.AXIS["z"])!=0 and
        rect_intersect(item1, item2, Vector3.AXIS["x"], Vector3.AXIS["z"])!=0
    )
