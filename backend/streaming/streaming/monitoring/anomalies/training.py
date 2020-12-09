import sys
from uuid import uuid4

from .db import build_dao
from .model import Model
from ..workers import report
from ...config import Config


def main(meeting_name, submission_date, calls):
    config = Config()
    dao = build_dao(config)
    training_data = dao.load_calls_data(meeting_name, calls)

    model_id = f'HBOS-{str(uuid4())}'
    model = Model(meeting_name, model_id)
    model.data = training_data
    # model.train()
    model.run_synthetic()
    report('training finished')

    dao.save_model(model, calls)
    report('model saved')

    dao.complete_training_job(meeting_name, submission_date)
    report('all done')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
