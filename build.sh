#!/bin/bash
pip install -r requirements.txt
python -c "import models; models.init_db()"