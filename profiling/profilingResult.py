import pandas as pd

df = pd.read_csv("./profiling/logs.csv", delimiter=';', index_col=None)
df['stop'] = pd.to_datetime(df['stop'], infer_datetime_format=True)
df['start'] = pd.to_datetime(df['start'], infer_datetime_format=True)
df['time'] = df['stop'] - df['start']
start_time = df['start'].min()
stop_time = df['stop'].max()
total_time = stop_time - start_time

groups = df.groupby(['name']).sum('time')
percentili = groups
percentili['count'] = df.groupby(['name']).count()['time']
percentili['time'] = percentili['time']
percentili['timepercall'] = percentili['time'] / percentili['count']
percentili['cost'] = percentili['time'] / percentili['count']
percentili['cost'] = percentili['cost'] / percentili['cost'].sum()
percentili['CPUtime%'] = percentili['time'] / total_time * 100

print("Free time: ", total_time - percentili['time'].sum())
print(percentili)