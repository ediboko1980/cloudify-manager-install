#!/opt/manager/env/bin/python

import argparse
import os
os.environ['MANAGER_REST_CONFIG_PATH'] = '/opt/manager/cloudify-rest.conf'  # NOQA

from manager_rest import server
from manager_rest.storage.models import Execution
from manager_rest.storage.models_states import ExecutionState


def _update_executions(dryrun=True):
    if dryrun:
        print 'Dry run - not sending writes to the database!'
    with server.app.app_context():
        query = (Execution.query.filter(
            server.db.or_(
                Execution.status == ExecutionState.CANCELLING,
                Execution.status == ExecutionState.FORCE_CANCELLING))
            .options(server.db.load_only(Execution.status, Execution.id))
        )

        for e in query.all():
            print 'Execution {0} status: changing {1} to {2}'.format(
                e.id, e.status, ExecutionState.CANCELLED)
            e.status = ExecutionState.CANCELLED
        if not dryrun:
            server.db.session.commit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--commit',
                        help='Save the changes. Without this, changes are '
                             'only printed out, but not persisted.',
                        dest='dryrun', action='store_false')
    args = parser.parse_args()
    _update_executions(dryrun=args.dryrun)
