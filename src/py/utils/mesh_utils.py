from models.index_type import IndexType

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

def read_indices(f, size):
    array = []
    for i in range(len(array)):
        num = 0
        if size == 2:
            num = int.from_bytes(f.read(2), byteorder="big", signed=False)
        else:
            num = int.from_bytes(f.read(4), byteorder="big", signed=False)
        if (size == 2 and num == 65535) or (size == 4 and num >= 16777215):
            num = -1
            array[i] = num
        # this is for car models
        #else:
            #array[i] = num + ForzaCarSection.IBoffset;
    return array