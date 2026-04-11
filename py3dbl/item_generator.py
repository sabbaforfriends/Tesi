from decimal import Decimal
from random import random,randint,gauss
from .Item import Item
from .Space import Vector3, Volume

def item_generator(width : tuple , height : tuple, depth : tuple, weight : tuple, priority_range : tuple[int,int] = (0,10), batch_size : int = 1, use_gaussian_distrib : bool = False, decimals : int = 3):
    """
    Generate Item objects with the given specifics
    
    :param width: Width min-max range or mu-sigma params
    :type width: tuple[Decimal, Decimal]
    :param height: Height min-max range or mu-sigma params
    :type height: tuple[Decimal, Decimal]
    :param depth: Depth min-max range or mu-sigma params
    :type depth: tuple[Decimal, Decimal]
    :param weight: Weight min-max range or mu-sigma params
    :type weight: tuple[Decimal, Decimal]
    :param priority_range: Priority min-max range
    :type priority_range: tuple[int, int]
    :param batch_size: Number of items to generate
    :type batch_size: int
    :param use_gaussian_distrib: if True size and weight are gaussian varibles and width,height,depth and weight are the mu-sigma params associated, if False size and weight are simple random variables and width,height,depth and weight are the minimum and maximum values
    :type use_gaussian_distrib: bool
    """
    
    randf = (lambda mu,sigma: abs(gauss(mu,sigma))) if use_gaussian_distrib else (lambda min,max: abs(min+random()*(max-min)))
    
    if batch_size == 1:
        return Item(
            name    = None,
            volume  = Volume(
                size = Vector3(
                    x=Decimal(randf(width[0],width[1])),
                    y=Decimal(randf(height[0],height[1])),
                    z=Decimal(randf(depth[0],depth[1]))
                )
            ),
            weight  = Decimal(randf(weight[0],weight[1])),
            priority= (randint(priority_range[0],priority_range[1]))
        )
    else:
        items = []
        for i in range(0,batch_size):
            item = Item(
                name    = str(i),
                volume  = Volume(
                    size = Vector3(
                        x=Decimal(randf(width[0],width[1])),
                        y=Decimal(randf(height[0],height[1])),
                        z=Decimal(randf(depth[0],depth[1]))
                    )
                ),
                weight  = Decimal(randf(weight[0],weight[1])),
                priority= (randint(priority_range[0],priority_range[1]))
            )
            items.append(item)
        return items