# Создайте исключение здесь
class LenTooLongError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
    def __str__(self) -> str:
        return super().__str__()


name = 'ЛилуминАй ЛекатАриба ЛаминачАй Экбат Дэ СэбАт'


def check_name(name):
    if len(name) > 4:
        # Вызовите исключение здесь
        raise LenTooLongError


check_name(name)