import {Component, OnInit} from '@angular/core';
import {MeetingsService} from '../../../services/meetings.service';
import {AllMeetings} from '../../meetings/class/all-meetings';

@Component({
  selector: 'app-third-card',
  templateUrl: './third-card.component.html',
  styleUrls: ['./third-card.component.scss']
})
export class ThirdCardComponent implements OnInit {

  constructor(
    private meetingsService: MeetingsService
  ) {
  }


  observedMeetings: string;
  activeMeetings: string;
  historicalMeetings: string;


  ngOnInit(): void {
    this.fetchMeetings();
  }

  fetchMeetings() {
    this.meetingsService.fetchMeetings().subscribe(
      res => {
        this.observedMeetings = '' + res.created.length;
        this.activeMeetings = '' + res.current.length;
        this.historicalMeetings = '' + res.recent.length;
      },
      err => {
        console.log(err);
        this.activeMeetings = '?';
        this.observedMeetings = '?';
        this.historicalMeetings = '?';
      }
    );
  }

}
