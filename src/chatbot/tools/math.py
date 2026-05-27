import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Use this tool when you need to calculate simple mathematical sums, products, differences, or divisions.
    
    Args:
        first_num: The first numeric value (operand).
        second_num: The second numeric value (operand).
        operation: The arithmetic operation to perform: 'add', 'sub', 'mul', or 'div'.
    
    Returns:
        A dictionary containing the input parameters and the computed 'result' or 'error' message.
    """
    logger.info(f"Calculator tool invoked: {first_num} {operation} {second_num}")
    try:
        operation = operation.strip().lower()
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}
        
        return {
            "first_num": first_num,
            "second_num": second_num,
            "operation": operation,
            "result": result
        }
    except Exception as e:
        logger.error(f"Error in calculator tool: {e}", exc_info=True)
        return {"error": str(e)}
