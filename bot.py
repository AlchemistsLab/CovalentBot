import requests
import telebot
import pandas as pd
import threading
import os.path

url = "https://api.covalenthq.com"
chain_id = "1"
my_key = "YOUR_COVALENT_API_KEY"

# CovalentBot
telegramm_token = "YOUR TELEGRAM_BOT_TOKEN"

bot = telebot.TeleBot(telegramm_token)

keyboard1 = telebot.types.ReplyKeyboardMarkup(True, True)
keyboard1.row('💰Balance', 'Show NFT image')
keyboard1.row('Add adr', 'Show adr', 'Edit adr', 'Del adr')
users_addr = {}



def address_balance(address):
    get_token_balances_for_address = f"/v1/{chain_id}/address/{address}/balances_v2/"
    result = requests.get(url + get_token_balances_for_address).json()
    result = result.get('data').get('items')
    df = pd.DataFrame(result)
    df = df[['contract_decimals', 'contract_name', 'balance']].loc[df['balance'] != '0'].loc[
         df['contract_decimals'] != 0]
    df['balance'] = round(df['balance'].astype('float') / (10 ** df['contract_decimals']), 2).astype('str')

    return df


def worker(event):
    while not event.isSet():
        if users_addr:
            for key, value in list(users_addr.items()):
                address = str(value)[2:-2]
                df = address_balance(address)

                if not os.path.isfile(address):
                    df.to_pickle(address)
                else:
                    df2 = pd.read_pickle(address)
                    result = pd.concat([df, df2]).drop_duplicates(keep=False)
                    if not result.empty:
                        for i in range(result.shape[0]):
                            bot.send_message(key, ''.join(result[['contract_name']].values[i]) + ' ' + ''.join(result[['balance']].values[i]))
                        df.to_pickle(address)

                event.wait(60)


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, 'Hello!', reply_markup=keyboard1)


@bot.message_handler(content_types=['text'])
def send_text(message):
    if message.text == '💰Balance':
        chat_id = message.chat.id
        if chat_id in users_addr:
            address = str(users_addr[chat_id])[2:-2]
            df = address_balance(address)
            if df.empty:
                bot.send_message(message.chat.id, text='There are no tokens on this address.')
            else:
                for i in range(df.shape[0]):
                    bot.send_message(message.chat.id,
                                     ''.join(df[['contract_name']].values[i]) + ' ' + ''.join(df[['balance']].values[i]))

        else:
            bot.send_message(message.chat.id, text='Set up your Eth address, please.')

    elif message.text == 'Show adr':
        chat_id = message.chat.id

        if chat_id in users_addr:
            bot.send_message(message.chat.id, text=users_addr[chat_id])
        else:
            bot.send_message(message.chat.id, text='Set up your Eth address, please.')

    elif message.text == 'Add adr':
        bot.send_message(message.chat.id, text='Input your Eth address:')
        bot.register_next_step_handler(message, add_adr)
        
    elif message.text == 'Edit adr':
        chat_id = message.chat.id
        if chat_id in users_addr:
            del users_addr[chat_id]
            bot.send_message(message.chat.id, text='Input new Eth address:')
            bot.register_next_step_handler(message, add_adr)   
        else:
            bot.send_message(message.chat.id, text='You do not have Eth address to edit.')    

    elif message.text == 'Del adr':
        chat_id = message.chat.id
        if chat_id in users_addr:
            del users_addr[chat_id]
            bot.send_message(message.chat.id, text='Your Eth address has been deleted.')
        else:
            bot.send_message(message.chat.id, text='You do not have Eth address to delete.')

    elif message.text == 'Show NFT image':
        chat_id = message.chat.id
        if chat_id in users_addr:
            address = str(users_addr[chat_id])[2:-2]
            get_nft_token_ids = f"/v1/{chain_id}/tokens/{address}/nft_token_ids/?page-size=5&key={my_key}"
            result = requests.get(url + get_nft_token_ids).json()
            result = result.get('data').get('items')

            if result:
                df = pd.DataFrame(result)[['token_id']]

                if not df.empty:
                    for token_id in df['token_id']:
                        get_external_nft_metadata = f"/v1/{chain_id}/tokens/{address}/nft_metadata/{token_id}/?&key={my_key}"
                        result = requests.get(url + get_external_nft_metadata).json()
                        try:
                            result = result.get('data').get('items')[0].get('nft_data')[0].get('external_data')
                            name = result.get('name')
                            image = result.get('image')
                            bot.send_photo(message.chat.id, requests.get(image).content, caption=name)
                        except:
                            None
                else:
                    bot.send_message(message.chat.id, text='There is no NFT at this address.')
            else:
                bot.send_message(message.chat.id, text='There is no NFT at this address.')
        else:
            bot.send_message(message.chat.id, text='Set up your Eth address, please.')


def add_adr(message):
    adr = message.text
    chat_id = message.chat.id
    users_addr[chat_id] = [adr]


event = threading.Event()
thread = threading.Thread(target=worker, args=(event,))
thread.start()

bot.polling()
