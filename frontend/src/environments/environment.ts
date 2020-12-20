// This file can be replaced during build by using the `fileReplacements` array.
// `ng build --prod` replaces `environment.ts` with `environment.prod.ts`.
// The list of file replacements can be found in `angular.json`.

export const environment = {
  production: false,
  backend: {
    rest: {
      url: 'http://localhost:5000',
      meetings: 'calls',
      public_meetings: 'meetings',
      anomalies: 'anomalies',
      reports: 'reports',
      models: 'models',
      notifications: 'notifications',
      monitoring: 'monitoring',
      logs: 'logs'

    },
    sse: {
      url: 'http://localhost:5001',
      notification: 'notifications',
      monitoring: 'monitoring',
      all: 'notifications',
      ml: 'anomaly-detection',
      train: 'anomaly-detection/train',
      evaluate: 'anomaly-detection/once',
      evaluate_admin: 'monitoring/once'
    }
  }
};

/*
 * For easier debugging in development mode, you can import the following file
 * to ignore zone related error stack frames such as `zone.run`, `zoneDelegate.invokeTask`.
 *
 * This import should be commented out in production mode because it will have a negative impact
 * on performance if an error is thrown.
 */
// import 'zone.js/dist/zone-error';  // Included with Angular CLI.
