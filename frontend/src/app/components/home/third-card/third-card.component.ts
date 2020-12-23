import {Component, OnInit} from '@angular/core';
import {MeetingsService} from '../../../services/meetings.service';

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
  mlMonitoring: string;
  adminMonitoring: string;
  adminCriteria: string;
  mlCriteria: string;
  onlineModel: string;


  ngOnInit(): void {
    this.fetchMeetings();
    this.fetchMonitoring();
  }

  fetchMonitoring() {
    this.meetingsService.fetchMonitoring().subscribe(
      res => {
        this.mlMonitoring = '' + res.ml_monitored.length;
        this.adminMonitoring = '' + res.admin_monitored.length;
        this.adminCriteria = '' + res.with_criteria.length;
        this.mlCriteria = '' + res.with_model.length;
        this.onlineModel = '' + res.with_online_model.length;
      }, err => {
        console.log(err);
        this.mlMonitoring = '?';
        this.adminMonitoring = '?';
        this.adminCriteria = '?';
        this.mlCriteria = '?';
        this.onlineModel = '?';
      });
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
