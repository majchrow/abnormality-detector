import {Component, OnInit} from '@angular/core';
import {Meetinginfo} from './class/meetinginfo';
import {MeetingsService} from '../../../services/meetings.service';

@Component({
  selector: 'app-second-card',
  templateUrl: './second-card.component.html',
  styleUrls: ['./second-card.component.scss']
})
export class SecondCardComponent implements OnInit {

  constructor(
    private meetingsService: MeetingsService
  ) {
  }

  options = {
    weekday: 'short',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  };

  infos: Array<Meetinginfo>;


  ngOnInit(): void {
    this.fetchNotifications();
  }

  manualSwitch(info: string) {
    switch (info) {
      case 'info': {
        return 'info';
      }
      case 'failure': {
        return 'warning';
      }
      case 'success': {
        return 'feedback';
      }
      default: {
        return 'info';
      }
    }
  }

  fetchNotifications() {
    this.meetingsService.fetchNotifications(5).subscribe(
      res => {
        const data: Meetinginfo[] = res.last.map(
          el => new Meetinginfo(
            el.name,
            new Date(Date.parse(el.timestamp)),
            el.event,
            this.manualSwitch(el.status)
          ));
        this.infos = data.reverse();
      }, err => {
        this.infos = [];
        console.log(err);
      }
    );
  }

  getStyle(info: string) {
    switch (info) {
      case 'info': {
        return {};
      }
      case 'warning': {
        return {color: 'red'};
      }
      case 'feedback': {
        return {color: '#388E3C'};
      }
      default: {
        return {};
      }
    }
  }

  move(event: MouseEvent) {}
}
