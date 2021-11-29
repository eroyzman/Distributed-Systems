from environs import Env

env = Env()

DELAY = env.int("DELAY", 0)
