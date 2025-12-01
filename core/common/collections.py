from collections import UserDict


class NestedDict(UserDict):
    def __getitem__(self, key):
        keys = key.split('.')

        data = self.data
        for i, k in enumerate(keys):
            if k in data:
                v = data[k]
                if keys[i+1:] and not hasattr(v, '__getitem__'):
                    raise ValueError(f'Not possible to get item from {v}')
                data = v
            else:
                raise KeyError(keys[:i+1])
        
        if isinstance(data, dict):
            return NestedDict(data)
        return data
    
    def to_dict(self):
        return {k: v.to_dict() if isinstance(v, NestedDict)
                else v if not isinstance(v, dict)
                else NestedDict(v).to_dict()
                for k, v in self.data.items()}
