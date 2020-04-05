from . import interact

interact(run_always=True)

# Raising an exception will trigger the PDB in the exception handler:
# raise AttributeError()

while True:
    import time
    time.sleep(1)
    print('hi')
