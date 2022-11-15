import time


def timer(func):
    def wrapper(*args, **kwargs):  # 引用外部作用域的变量func
        start_time = time.time()
        res = func(*args, **kwargs)
        stop_time = time.time()
        print('run time is %s' % (stop_time - start_time))
        return res

    return wrapper  # return a function


# decorator function must be putting above the function being decorated
@timer
def testing_func(a_number: float):
    time.sleep(3)
    print("testing testing testing " + str(a_number))


if __name__ == '__main__':
    testing_func(122)
