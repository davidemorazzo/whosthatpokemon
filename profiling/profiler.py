from datetime import datetime

class BaseProfiler():
	def __init__(self, descr:str):
		self.start = datetime.now()
		self.stop = None
		self.description=descr
		self.outFile = "./logs.csv"

	def __del__(self):
		self.stop = datetime.now()
		delta = (self.stop - self.start).microseconds
		with open(self.outFile, 'a') as f:
			f.write(f"{self.description};{delta}\n")

	