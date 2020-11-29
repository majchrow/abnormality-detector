import {Injectable} from '@angular/core';
import {HttpClient} from '@angular/common/http';
import {environment} from '../../environments/environment';
import {Observable} from 'rxjs';
import {AllMeetings} from '../components/meetings/class/all-meetings';
import {Meeting} from '../components/meetings/class/meeting';
import {HistorySpec} from '../components/meetings/meeting-history/class/history';

@Injectable({
  providedIn: 'root'
})
export class MeetingsService {


  private backend = environment.backend.rest;

  constructor(private http: HttpClient) {
  }


  putMeeting(meeting: Meeting): Observable<any> {
    const url = `${this.backend.url}/${this.backend.meetings}`;
    return this.http.put(url, meeting);
  }

  deleteMeeting(meeting: Meeting): Observable<any> {
    const url = `${this.backend.url}/${this.backend.meetings}?name=${meeting.name}`;
    return this.http.delete(url);
  }

  fetchMeeting(name: string): Observable<Meeting> {
    const url = `${this.backend.url}/${this.backend.meetings}/${name}`;
    return this.http.get<Meeting>(url);
  }

  fetchMeetings(): Observable<AllMeetings> {
    const url = `${this.backend.url}/${this.backend.meetings}`;
    return this.http.get<AllMeetings>(url);
  }

  fetchAnomalies(meeting: Meeting, count: number): Observable<any> {
    const url = `${this.backend.url}/${this.backend.anomalies}?name=${meeting.name}&count=${count}`;
    return this.http.get<any>(url);
  }

}
