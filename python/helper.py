# Util
import logging
from pathlib import Path

# Self
prompt_name_list = ["prompt"]
logger = logging.getLogger("app")
PROMPT_DIR = Path(__file__).resolve().parent.parent

# ===============================
# LLM
# ===============================

def _grab_system_prompt(prompt_name_index: int = 0) -> str:
    """
    Retrieve System Prompt from prompts folder
    Args:
        prompt_name_index (int): System Prompt index inside prompt_name_list

    Raises:
        IndexError: Wrong Index, Out of range

    Returns:
        prompt:  System Prompt extracted from prompts folder
    """
    try:
        # Confirms prompts exist
        if (prompt_name_index < 0 or prompt_name_index >= len(prompt_name_list)):
            raise IndexError("Prompt not found. ")

        # Resolve prompt file from project root, independent of current working directory.
        file_path = PROMPT_DIR / f"{prompt_name_list[prompt_name_index]}.txt"
        with file_path.open(mode="r", encoding="utf-8") as file:
            prompt: str = file.read()
            return prompt
        
    # Catch file-system related errors (FileNotFound, DirNotFound)
    except (FileNotFoundError, NotADirectoryError):
        raise ValueError(f"Prompt file or directory not found at {file_path}") from None
    except IndexError:
        raise IndexError(
            f"Prompt File Name List Index out of range error. Index: {prompt_name_index}. "
            f"Max Index: {len(prompt_name_list)-1}"
        )
    except Exception as e:
        # Re-raise any other unexpected errors (like permission issues)
        raise Exception(f"Error while extracting system prompt: {e}")
    
# ===============================
# Output Formatting
# ===============================
    
def _format_response(response: str) -> str | None:
    """
    Format the output response to the top CSV item only.
    Args:
        prompt_name_index (int): System Prompt index inside prompt_name_list
    """
    try:
        cleaned = response.replace("\n", "").strip()
        if not cleaned:
            return None
        items = [item.strip() for item in cleaned.split(",") if item.strip()]
        return items[0] if items else None
    except Exception:
        logger.exception("Error formatting response")
        return None