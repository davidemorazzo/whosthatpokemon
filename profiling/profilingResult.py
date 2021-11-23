import pandas as pd

df = pd.read_csv("./logs.csv", delimiter=';', index_col=None)
tot_time = df['time'].sum()
groups = df.groupby(['name']).sum()
percentili = groups / tot_time
percentili['count'] = df.groupby(['name']).count()
percentili['time'] = percentili['time'] / percentili['count']
percentili['cost'] = percentili['time'] / percentili['time'].sum()
print(percentili)