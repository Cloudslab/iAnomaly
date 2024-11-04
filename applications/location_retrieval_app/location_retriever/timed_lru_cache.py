"""
A python class that works as a timed LRU cache.
This is inspired by the following works:
https://realpython.com/lru-cache-python/
https://www.geeksforgeeks.org/lru-cache-in-python-using-ordereddict/
"""

import datetime
from collections import OrderedDict
from typing import Union, List


class TimedLRUCache:

    def __init__(self, cache_size: int, time_limit: datetime.timedelta):
        """
        An LRU Cache with a time limit.
        :param cache_size: Max number of entries that can be held in cache
        :param time_limit: Max seconds cache will hold an entry
        """
        self.cache = OrderedDict()
        self.cache_size = cache_size
        self.cache_time_limit = time_limit

    def __getitem__(self, key: int) -> Union[List, None]:
        """
        Retrieves and returns an entry from the cache, if available.
        If not found returns None.
        :param key: key of the entry to be retrieved
        :return: a list containing [latitude,longitude], None if the key is not present or expired.
        """

        if key not in self.cache:
            return None
        else:
            if self.cache[key][1] < datetime.datetime.utcnow():
                return None
            else:
                self.cache.move_to_end(key)
                return self.cache[key][0]

    def __setitem__(self, key: int, value: Union[List, dict]) -> None:
        """
        Saves a new value into the cache
        :param key: the key of the entry
        :param value: value of the entry
        :return: None
        """

        if len(self.cache) >= self.cache_size:
            self.cache.popitem(last=False)
        expire_time = datetime.datetime.utcnow() + self.cache_time_limit
        self.cache[key] = (value, expire_time)
        self.cache.move_to_end(key)