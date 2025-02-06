from multiprocessing import Value

# Shared variable `busy`
busy = Value('b', False)  # 'b' indicates a boolean value