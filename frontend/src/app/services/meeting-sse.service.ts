import {Injectable, NgZone} from '@angular/core';
import {Observable, Observer} from 'rxjs';
import {environment} from '../../environments/environment';
import {HttpClient} from '@angular/common/http';

@Injectable({
  providedIn: 'root'
})
export class MeetingSSEService {

  private backend = environment.backend.sse;

  constructor(
    private zone: NgZone,
    private http: HttpClient
  ) {
  }

  private static getEventSource(url: string): EventSource {
    return new EventSource(url);
  }


  fetchMonitoring(name: string): Observable<any> {
    const url = `${this.backend.url}/${this.backend.monitoring}/${name}`;
    return this.http.get<any>(url);
  }

  putMonitoring(meeting): Observable<any> {
    const url = `${this.backend.url}/${this.backend.monitoring}/${meeting.name}?type=threshold`;
    const payload = {
      type: 'threshold',
      criteria: meeting.criteria
    };
    return this.http.put(url, payload);
  }

  deleteMonitoring(meeting): Observable<any> {
    const url = `${this.backend.url}/${this.backend.monitoring}/${meeting.name}?type=threshold`;
    return this.http.delete(url);
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
    const url = `${this.backend.url}/${this.backend.notification}`;
    return this._getObservable(url);
  }

  getServerSentEvent(name: string): Observable<any> {
    const url = `${this.backend.url}/${this.backend.notification}/${name}?type=threshold`;
    return this._getObservable(url);
  }

}

