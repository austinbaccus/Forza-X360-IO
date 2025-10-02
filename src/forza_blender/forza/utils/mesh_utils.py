from ..models.index_type import IndexType
from ..models.forza_vertex import ForzaVertex
from typing import List, Dict

def calculate_face_count(indices, index_type):
    if index_type == IndexType.TriStrip:
        num = 0
        num2 = 0
        while num < len(indices) - 2:
            if indices[num + 2] != -1:
                num = num + 1
                num2 = num2 + 1
            else:
                num = num + 3
        return num2
    elif index_type == IndexType.TriList:
        return len(indices) / 3
    else:
        raise TypeError("Unknown index type.")

def calculate_vertex_count(indices):
    hashtable = {}
    for num in indices:
        if num != -1:
            hashtable[num] = 0
    return len(hashtable)

def read_indices(f, count, size):
    array = []
    for i in range(count):
        num = 0
        if size == 2:
            num = int.from_bytes(f.read(2), byteorder="big", signed=False)
        else:
            num = int.from_bytes(f.read(4), byteorder="big", signed=True)
        if (size == 2 and num == 65535) or (size == 4 and num >= 16777215):
            num = -1
            array.append(num)
        else:
            # TODO this is for stuff like cones and whatnot, not just cars, so this should be a little higher priority to get working.
            array.append(num) # + ForzaCarSection.IBoffset; # this is 0 unless FM2
    return array

def generate_triangle_list(indices: List[int], face_count: int) -> List[int]:
    array = [0] * (face_count * 3)
    flag = True
    num = 0
    num2 = 0

    while num < len(indices) - 2:
        num3 = indices[num + 2]
        if num3 != -1:
            num4 = indices[num]
            num5 = indices[num + 1]
            num += 1
            if num4 != num5 and num5 != num3 and num4 != num3:
                if flag:
                    array[num2] = num4
                    array[num2 + 1] = num5
                    array[num2 + 2] = num3
                else:
                    array[num2] = num5
                    array[num2 + 1] = num4
                    array[num2 + 2] = num3
            num2 += 3
            flag = not flag
        else:
            flag = True
            num += 3

    return array

def generate_vertices(section_vertices: List[ForzaVertex], sub_section_indices: List[int]) -> List[ForzaVertex]:
    num = 0
    hashtable: Dict[int, int] = {}
    num2 = len(sub_section_indices)

    for i in range(num2):
        num3 = sub_section_indices[i]
        if num3 != -1:
            if num3 not in hashtable:
                hashtable[num3] = num
                num += 1
            sub_section_indices[i] = hashtable[num3]

    array: List[ForzaVertex] = [None] * num 

    for key, value in hashtable.items():
        array[value] = section_vertices[key]

    return array