import pytest  
from your_module import format_response  # Replace with actual module name  
  
def test_format_response():  
    response = "BOH Bee Honey Mask, BOH Green Tea Essence, BOH Probiotic Lotion"  
    expected_output = "BOH Bee Honey Mask"  
    assert format_response(response) == expected_output  