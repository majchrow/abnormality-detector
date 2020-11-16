import {Injectable, NgZone} from '@angular/core';
import {Observable, Observer} from 'rxjs';
import {environment} from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class MeetingSSEService {

  private backend = environment.backend.sse;

  constructor(private zone: NgZone) {
  }

  private static getEventSource(url: string): EventSource {
    return new EventSource(url);
  }


  _getObservable(url: string) {
    return new Observable((observer: Observer<any>) => {
      const eventSource = MeetingSSEService.getEventSource(url);
      eventSource.onmessage = event => {
        this.zone.run(() => {
          observer.next(event);
        });
      };

      eventSource.onerror = error => {
        this.zone.run(() => {
          observer.error(error);
        });
      };
    });
  }

  getServerSentEvents(): Observable<any> {
    const url = `${this.backend.url}/${this.backend.all}`;
    return this._getObservable(url);
  }

  getServerSentEvent(name: string): Observable<any> {

    const url = `${this.backend.url}/${this.backend.notification}${name}`;
    return this._getObservable(url);
  }

}

