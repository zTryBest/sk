# -*- coding: utf-8 -*-

from typing import Any, Dict


def success(data: Any, msg: str = "OK") -> Dict:
    return {
        "success": True,
        "message": msg,
        "data": data
    }


def error(msg: str) -> Dict:
    return {
        "success": False,
        "message": msg,
        "data": None
    }
