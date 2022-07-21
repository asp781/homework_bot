import requests
import os
import sys
import time
import logging
from logging import StreamHandler
from dotenv import load_dotenv
import telegram
from http import HTTPStatus


load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(funcName)s, %(lineno)s',    
    filemode='a'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=sys.stdout)
formatter = logging.Formatter('%(asctime)s, %(levelname)s, %(message)s,')
handler.setFormatter(formatter)
logger.addHandler(handler)

PRACTICUM_TOKEN = 'AQAAAAACb6POAAYckSBl3AMwq0h8r7Fs-dp_rDs'
# PRACTICUM_TOKEN = 0
TELEGRAM_TOKEN = '5400441580:AAEGMJnIPkjNjqUg5pG6sZyH0ERFXU-oJ7o'
# TELEGRAM_TOKEN = ''
TELEGRAM_CHAT_ID = 563177556
# TELEGRAM_CHAT_ID = 0

RETRY_TIME = 3
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):    
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Сообщение "{message}" отправлено в Telegram')
    except Exception:
        logging.exception(f'Сбой при отправке сообщения "{message}" в Telegram')    
    

def get_api_answer(current_timestamp):    
    timestamp = current_timestamp# or int(time.time())
    # timestamp = 0 # критичен для тестов
    # print(current_timestamp, timestamp)
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception:
        logging.exception('Сбой при запросе к эндпоинту')    
    
    if response.status_code != HTTPStatus.OK:
        logging.exception(f'Эндпоинт недоступен: {response.status_code}')
        raise Exception(f'Эндпоинт недоступен: {response.status_code}')    
    return response.json() 
    # return response.text   


def check_response(response):    
    try:
        homeworks = response['homeworks']
    except TypeError:
        logger.error('Ответ от API не является словарем')
        raise TypeError('Ответ от API не является словарем')
    if type(homeworks) != list:
        logger.error('Под ключом `homeworks` ответ от API не в виде списка')
        raise TypeError('Под ключом `homeworks` ответ от API не в виде списка')         
    return homeworks # список заданий, может быть пустым


def parse_status(homework):    
    if 'homework_name' not in homework:
        logger.error('Отсутствует ожидаемый ключ "homework_name" в ответе API')
        raise KeyError('Отсутствует ожидаемый ключ "homework_name" в ответе API')
    if 'status' not in homework:
        logger.error('Отсутствует ожидаемый ключ "status" в ответе API')
        raise KeyError('Отсутствует ожидаемый ключ "status" в ответе API')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        logger.error(f'Недокументированный статус домашней работы: {homework_status}')
        raise Exception(f'Недокументированный статус домашней работы: {homework_status}')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():    
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:        
        return True
    return False


def main():
    """Основная логика работы бота."""   
    if check_tokens() == False:
        logger.critical('Отсутствуют одна или несколько переменных окружения')          
        raise Exception('Отсутствуют одна или несколько переменных окружения')
    
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    
    OLD_MESSAGE = ''
              
    x = 0
    while x == 0:
    # while True:    
        try:
            response = get_api_answer(current_timestamp)            
            try:
                message = parse_status(check_response(response)[0])
            except IndexError:
                message = 'Изменений нет'
            # if message != OLD_MESSAGE:
            #     send_message(bot, message) # переместить в else
            #     OLD_MESSAGE = message
            current_timestamp = response.get('current_date') # проверить изменения
            print(current_timestamp)
            time.sleep(RETRY_TIME)
        
        except Exception as error:        
            message = f'Сбой в работе программы: {error}'            
            # if message != OLD_MESSAGE:
            #     send_message(bot, message) # переместить в else 
            #     OLD_MESSAGE = message
            time.sleep(RETRY_TIME)
        
        finally:
            if message != OLD_MESSAGE:
                    send_message(bot, message)
                    OLD_MESSAGE = message   
        x = 1


if __name__ == '__main__':
    main()