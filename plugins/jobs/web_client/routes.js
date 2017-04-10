import router from 'girder/router';
import events from 'girder/events';

import JobModel from './models/JobModel';
import JobDetailsWidget from './views/JobDetailsWidget';
import JobList from './views/JobList';

router.route('job/:id', 'jobView', function (id) {
    var job = new JobModel({ _id: id }).once('g:fetched', function () {
        events.trigger('g:navigateTo', JobDetailsWidget, {
            job: job,
            renderImmediate: true
        });
    }, this).once('g:error', function () {
        router.navigate('collections', { trigger: true });
    }, this);
    job.fetch();
});

router.route('jobs/user/:id(/:view)', 'jobList', function (id, view) {
    events.trigger('g:navigateTo', JobList, {
        filter: { userId: id },
        view: view
    });
});

router.route('jobs(/:view)', 'allJobList', function (view) {
    events.trigger('g:navigateTo', JobList, {
        allJobsMode: true,
        view: view
    });
});
