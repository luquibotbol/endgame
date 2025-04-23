import aiohttp
import logging
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime, timedelta
import sys
import os
from pathlib import Path
import numpy as np
from collections import defaultdict
from textblob import TextBlob  # For sentiment analysis
from sklearn.linear_model import LinearRegression
import pandas as pd
from typing import NamedTuple

# Add masa-mcp to Python path and import twitter_search
masa_mcp_path = str(Path(__file__).parent.parent.parent / 'masa-mcp' / 'src')
sys.path.append(masa_mcp_path)
from main import twitter_search

logger = logging.getLogger(__name__)

# ... existing code ... 