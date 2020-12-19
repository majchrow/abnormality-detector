import {Injectable} from '@angular/core';
import {HttpClient, HttpHeaders} from '@angular/common/http';
import {environment} from '../../environments/environment';
import {Observable} from 'rxjs';
import {AllMeetings} from '../components/meetings/class/all-meetings';
import {Meeting} from '../components/meetings/class/meeting';
import {HistoryMeeting} from '../components/meetings/meeting-history/class/history-meeting';

@Injectable({
  providedIn: 'root'
})
export class MeetingsService {


  private backend = environment.backend.rest;

  constructor(private http: HttpClient) {
  }


  putMeeting(meeting: Meeting): Observable<any> {
    const url = `${this.backend.url}/${this.backend.public_meetings}`;
    return this.http.put(url, {
      name: meeting.name,
      criteria: meeting.criteria,
    });
  }

  getAllReports(meeting: Meeting): Observable<any> {
    let headers = new HttpHeaders();
    headers = headers.set('Accept', 'application/pdf');
    const url = `${this.backend.url}/${this.backend.reports}/${meeting.name}`;
    console.log(url);
    return this.http.get(url, {headers, responseType: 'blob' as 'json'});
  }

  getModelInfo(meeting: Meeting): Observable<any> {
    const url = `${this.backend.url}/${this.backend.models}/${meeting.name}`;
    return this.http.get<any>(url);
  }

  getReports(meeting: Meeting, historyMeeting: HistoryMeeting): Observable<any> {
    let headers = new HttpHeaders();
    headers = headers.set('Accept', 'application/pdf');
    const url = `${this.backend.url}/${this.backend.reports}/${meeting.name}?start_datetime=${historyMeeting.start.toISOString()}`;
    console.log(url);
    return this.http.get(url, {headers, responseType: 'blob' as 'json'});
  }

  deleteMeeting(meeting: Meeting): Observable<any> {
    const url = `${this.backend.url}/${this.backend.public_meetings}?name=${meeting.name}`;
    return this.http.delete(url);
  }

  fetchMeeting(name: string): Observable<Meeting> {
    const url = `${this.backend.url}/${this.backend.public_meetings}/${name}`;
    return this.http.get<Meeting>(url);
  }

  fetchMeetingHistory(name: string): Observable<any> {
    const url = `${this.backend.url}/${this.backend.meetings}/${name}`;
    return this.http.get<any>(url);
  }

  fetchMeetingHistoryModel(name: string, start: Date, end: Date, minParticipants: number, duration: number): Observable<any> {
    const url = `${this.backend.url}/${this.backend.meetings}/${name}?start=${start.toISOString()}&end=${end.toISOString()}&min_duration=${duration}&max_participants=${minParticipants}`;
    return this.http.get<any>(url);
  }

  fetchMeetings(): Observable<AllMeetings> {
    const url = `${this.backend.url}/${this.backend.meetings}`;
    return this.http.get<AllMeetings>(url);
  }

  fetchPublicMeetings(): Observable<any> {
    const url = `${this.backend.url}/${this.backend.public_meetings}`;
    return this.http.get<any>(url);
  }

  fetchAnomalies(meeting: Meeting): Observable<any> {
    const url = `${this.backend.url}/${this.backend.anomalies}/${meeting.name}`;
    console.log(url);
    return this.http.get<any>(url);
  }

  fetchAnomaliesHistory(meeting: Meeting, historyMeeting: HistoryMeeting): Observable<any> {
    const url = `${this.backend.url}/${this.backend.anomalies}/${meeting.name}?start=${historyMeeting.start.toISOString()}&end=${historyMeeting.end.toISOString()}`;
    console.log(url);
    return this.http.get<any>(url);
  }

}
