class NotFoundError(Exception):
    def __init__(self, obj, message='not found'):
        self.obj = obj
        self.message = message

    def __str__(self):
        return f"{self.obj}: {self.message}"


class AddressNotFoundError(NotFoundError):
    def __init__(self, address, message="address was not found"):
        self.message = message
        self.address = address
        super().__init__(self.address, self.message)

    
class StopNotFoundError(NotFoundError):
    def __init__(self, stop=None, message='stop was not found', **kwargs):
        stop_name = kwargs.get('stop_name')
        stop_code = kwargs.get('stop_code')
        
        if not stop:
            stop = f'{stop_name} {stop_code}'
        else:
            if isinstance(stop, dict):
                stop = f'{stop['stop_name']} {stop['stop_code']}'
            else:
                stop = f'{stop.stop_name} {stop.stop_code}'

        self.stop = stop
        self.message = message
        super().__init__(self.stop, self.message)