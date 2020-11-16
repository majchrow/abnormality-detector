import {Injectable} from '@angular/core';
import {HttpClient} from '@angular/common/http';
import {environment} from '../../environments/environment';
import {Observable} from 'rxjs';
import {AllMeetings} from '../components/meetings/class/all-meetings';

@Injectable({
  providedIn: 'root'
})
export class MeetingsService {


  private backend = environment.backend.rest;

  constructor(private http: HttpClient) {
  }


  fetch_meetings(): Observable<AllMeetings> {
    const url = `${this.backend.url}/${this.backend.meetings}`;
    return this.http.get<AllMeetings>(url);
  }

}
