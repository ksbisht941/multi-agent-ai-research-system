import pytest
from chatbot.tools.math import calculator
from chatbot.tools.scheduler import generate_day_plan

def test_calculator_operations():
    """
    Verifies that the math tool performs standard arithmetic correctly.
    """
    # Addition
    res = calculator.invoke({"first_num": 10, "second_num": 5, "operation": "add"})
    assert res["result"] == 15
    
    # Subtraction
    res = calculator.invoke({"first_num": 10, "second_num": 5, "operation": "sub"})
    assert res["result"] == 5
    
    # Multiplication
    res = calculator.invoke({"first_num": 10, "second_num": 5, "operation": "mul"})
    assert res["result"] == 50
    
    # Division
    res = calculator.invoke({"first_num": 10, "second_num": 5, "operation": "div"})
    assert res["result"] == 2.0

def test_calculator_division_by_zero():
    """
    Ensures division by zero is handled safely with a friendly error response.
    """
    res = calculator.invoke({"first_num": 10, "second_num": 0, "operation": "div"})
    assert "error" in res
    assert "zero" in res["error"].lower()

def test_calculator_invalid_operation():
    """
    Ensures invalid operation strings return an error message.
    """
    res = calculator.invoke({"first_num": 10, "second_num": 5, "operation": "integrate"})
    assert "error" in res
    assert "unsupported" in res["error"].lower()

def test_generate_day_plan():
    """
    Verifies that list tasks are converted to time blocks correctly.
    """
    tasks = ["Morning run", "Write tests", "Investor sync"]
    res = generate_day_plan.invoke({"tasks": tasks, "start_hour": 8})
    
    assert "schedule" in res
    assert len(res["schedule"]) == 3
    
    first = res["schedule"][0]
    assert first["start"] == "08:00"
    assert first["end"] == "09:00"
    assert first["task"] == "Morning run"
    
    last = res["schedule"][2]
    assert last["start"] == "10:00"
    assert last["end"] == "11:00"
    assert last["task"] == "Investor sync"
