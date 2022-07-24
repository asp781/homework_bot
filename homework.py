import json
import logging
import os
import sys
import time
from http import HTTPStatus
from logging import StreamHandler

import requests
import telegram
from dotenv import load_dotenv
from telegram import TelegramError

from exceptions import CustomError

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

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат, определяемый TELEGRAM_CHAT_ID.
    Принимает на вход два параметра: экземпляр класса Bot
    и строку с текстом сообщения.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Сообщение "{message}" отправлено в Telegram')
    except TelegramError:
        logger.error(f'Сбой при отправке сообщения "{message}" Telegram')
        raise TelegramError(f'Сбой при отправке сообщения "{message}"Telegram')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра функция получает временную метку.
    В случае успешного запроса должна вернуть ответ API,
    преобразовав его из формата JSON к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.exceptions.ConnectionError:
        logger.error('Проблемы с сетью')
        raise requests.exceptions.ConnectionError('Проблемы с сетью')
    except requests.exceptions.Timeout:
        logger.error('Время ожидания запроса истекло')
        raise requests.exceptions.Timeout('Время ожидания запроса истекло')
    except requests.exceptions.TooManyRedirects:
        logger.error('URL-адрес был неправильным')
        raise requests.exceptions.TooManyRedirects(
            'URL-адрес был неправильным'
        )
    except requests.exceptions.RequestException:
        logger.error('Сбой при запросе к эндпоинту')
        raise requests.exceptions.RequestException(
            'Сбой при запросе к эндпоинту'
        )
    if response.status_code != HTTPStatus.OK:
        logger.error(f'Эндпоинт недоступен: {response.status_code}')
        raise CustomError(f'Эндпоинт недоступен: {response.status_code}')
    try:
        response = response.json()
    except json.decoder.JSONDecodeError:
        logger.error('Ответ не является типом данный Python')
        raise json.decoder.JSONDecodeError(
            'Ответ не является типом данный Python'
        )
    return response


def check_response(response):
    """Проверяет ответ API на корректность.
    В качестве параметра функция получает ответ API, приведенный
    к типам данных Python. Если ответ API соответствует ожиданиям,
    то функция должна вернуть список домашних работ (он может быть и пустым),
    доступный в ответе API по ключу 'homeworks'.
    """
    try:
        homeworks = response['homeworks']
    except TypeError:
        logger.error('Ответ от API не является словарем')
        raise TypeError('Ответ от API не является словарем')
    except KeyError:
        logger.error('Ключ "homeworks" отсутствует в словаре')
        raise KeyError('Ключ "homeworks" отсутствует в словаре')
    if type(homeworks) is not list:
        logger.error('Под ключом `homeworks` ответ от API не в виде списка')
        raise TypeError('Под ключом `homeworks` ответ от API не в виде списка')
    return homeworks


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус этой работы.
    В качестве параметра функция получает только один элемент из списка
    домашних работ. В случае успеха, функция возвращает подготовленную для
    отправки в Telegram строку, содержащую один из вердиктов словаря
    HOMEWORK_STATUSES.
    """
    if 'homework_name' not in homework:
        logger.error('Отсутствует ожидаемый ключ "homework_name" в ответе')
        raise KeyError('Отсутствует ожидаемый ключ "homework_name" в ответе')
    if 'status' not in homework:
        logger.error('Отсутствует ожидаемый ключ "status" в ответе API')
        raise KeyError('Отсутствует ожидаемый ключ "status" в ответе API')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        logger.error(f'Недокументированный статус: {homework_status}')
        raise Exception(f'Недокументированный статус: {homework_status}')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения.
    Если отсутствует хотя бы одна переменная окружения —
    функция должна вернуть False, иначе — True.
    """
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    return False


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствуют одна или несколько переменных окружения')
        raise Exception('Отсутствуют одна или несколько переменных окружения')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    old_message = ''
    try:
        while True:
            try:
                response = get_api_answer(current_timestamp)
                try:
                    message = parse_status(check_response(response)[0])
                except IndexError:
                    message = 'Изменений нет'
                current_timestamp = response.get('current_date')
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
            finally:
                if message != old_message:
                    send_message(bot, message)
                    old_message = message
                time.sleep(RETRY_TIME)
    except KeyboardInterrupt:
        print('Работа бота завершена!')


if __name__ == '__main__':
    main()
