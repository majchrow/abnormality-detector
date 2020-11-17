// This file can be replaced during build by using the `fileReplacements` array.
// `ng build --prod` replaces `environment.ts` with `environment.prod.ts`.
// The list of file replacements can be found in `angular.json`.

export const environment = {
  production: false,
  backend: {
    rest: {
      url: 'http://localhost:5000', // TODO, how to pass linked service name without nginx
      meetings: 'conferences'
    },
    sse: {
      url: 'http://localhost:5001', // TODO
      notification: 'notifications?conf_name=',
      monitoring: 'monitoring',
      all: 'notifications' // TODO
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
