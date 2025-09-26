


def bound(low, v, high):
    return max(low, min(v, high))

def saveAvg(l):

    if l:
        return sum(l) / len(l)
    return 0

