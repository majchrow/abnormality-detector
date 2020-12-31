import {Injectable, NgZone} from '@angular/core';
import {Observable, Observer} from 'rxjs';
import {environment} from '../../environments/environment';
import {HttpClient} from '@angular/common/http';
import {Meeting} from '../components/meetings/class/meeting';
import {HistoryMeeting} from '../components/meetings/meeting-history/class/history-meeting';

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

      return () => {
        eventSource.close();
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

  trainModel(meeting: Meeting, calls: string[], threshold: number, minDuration: number, maxParticipants: number, retrain: boolean): Observable<any> {
    const url = `${this.backend.url}/${this.backend.train}/${meeting.name}`;
    const payload = {
      calls,
      threshold: threshold / 100,
    };
    if (retrain) {
      payload['retrain'] = {
          min_duration: minDuration,
          max_participants: maxParticipants
      };
    }
    return this.http.put(url, payload);
  }

  evaluateModel(meeting: Meeting, calls: string[], threshold: number, historyMeeting: HistoryMeeting): Observable<any> {
    const url = `${this.backend.url}/${this.backend.evaluate}/${meeting.name}`;
    let end;
    try {
      end = historyMeeting.end.toISOString();
    } catch (e) {
      end = new Date().toISOString();
    }
    const payload = {
      training_calls: calls,
      threshold: threshold / 100,
      start: historyMeeting.start.toISOString(),
      end
    };
    console.log(payload);
    return this.http.put(url, payload);
  }

  evaluateAdminModel(meeting: Meeting, historyMeeting: HistoryMeeting): Observable<any> {
    const url = `${this.backend.url}/${this.backend.evaluate_admin}/${meeting.name}`;
    let end;
    try {
      end = historyMeeting.end.toISOString();
    } catch (e) {
      end = new Date().toISOString();
    }
    const payload = {
      name: meeting.name,
      criteria: meeting.criteria,
      start: historyMeeting.start.toISOString(),
      end
    };
    console.log(payload);
    return this.http.put(url, payload);
  }

  getMLMonitoring(meeting): Observable<any> {
    const url = `${this.backend.url}/${this.backend.ml}/${meeting.name}`;
    return this.http.get(url, {});
  }

  putMLMonitoring(meeting): Observable<any> {
    const url = `${this.backend.url}/${this.backend.ml}/${meeting.name}`;
    return this.http.put(url, {});
  }

  deleteMLMonitoring(meeting): Observable<any> {
    const url = `${this.backend.url}/${this.backend.ml}/${meeting.name}`;
    return this.http.delete(url, {});
  }

}

