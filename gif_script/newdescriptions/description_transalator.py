import pandas as pd
from googletrans import Translator
import asyncio

def translate(idx, df:pd.DataFrame, col_name:str, lang:str):
	translator = Translator()
	translated = translator.translate(df.loc[idx, 'en'], dest=lang)
	df.loc[idx, col_name] = translated.text
	return df

async def main():
	pokemon_data = pd.read_csv('str/descriptions.csv', index_col='name')
	description_df = pd.read_csv('str/descriptions.csv', index_col='name')
	t = []
	loop = asyncio.get_event_loop()
	for lang in ['fr', 'es', 'it', 'ko', 'de', 'hi', 'ja', 'zh-cn']:
		col_name = lang.replace('zh-cn', 'zh').replace('ja', 'jp')
		for idx in pokemon_data[pokemon_data[col_name].isna()].index:
			t1 = loop.run_in_executor(None, translate, idx, description_df, col_name, lang)
			t.append(t1)
	
	t = [i for i in t if i.done()==False]
	while len(t) > 0:
		print(len(t))
		await asyncio.sleep(0.1)
		t = [i for i in t if i.done()==False]
	
	await asyncio.sleep(1)
	description_df.to_csv('str/descriptions.csv')
	pass
	



if __name__ == '__main__':
	asyncio.run(main())