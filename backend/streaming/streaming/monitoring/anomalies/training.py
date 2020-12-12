import sys

from .db import build_dao
from .model import Model
from ..workers import report
from ...config import Config


# TODO:
#  - job doesn't exist
#  - no training data
#  - other failures during training?
def main(job_id):
    config = Config()
    dao = build_dao(config)
    job = dao.load_training_job(job_id)
    report(f'loaded training job {job_id}')

    ci_df, roster_df = dao.load_calls_data(job['meeting_name'], job['training_call_starts'])
    report(f'loaded training data for {job_id}: call-info {ci_df.shape}, roster {roster_df.shape}')

    ci_model = Model(job['meeting_name'])
    roster_model = Model(job['meeting_name'])

    ci_model.train(ci_df)
    report('call info training finished')

    roster_model.train(roster_df)
    report('roster training finished')

    dao.save_models(ci_model, roster_model, job['training_call_starts'])
    report('models saved')

    dao.complete_training_job(job_id)
    report('all done')


if __name__ == '__main__':
    main(sys.argv[1])
