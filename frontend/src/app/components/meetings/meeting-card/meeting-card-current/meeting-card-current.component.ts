import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Meeting} from '../../class/meeting';
import {Observable} from 'rxjs';

@Component({
  selector: 'app-meeting-card-current',
  templateUrl: './meeting-card-current.component.html',
  styleUrls: ['./meeting-card-current.component.scss']
})
export class MeetingCardCurrentComponent implements OnInit {

  @Input() meeting: Meeting;
  @Output() historyEmitter = new EventEmitter<Meeting>();
  @Output() settingEmitter = new EventEmitter<Meeting>();

  monitoring: Observable<any>;
  monitored = false;

  constructor() {
  }

  ngOnInit(): void {
  }


  onSettingClick() {
    this.settingEmitter.emit(this.meeting);
  }

  onHistoryClick() {
    this.historyEmitter.emit(this.meeting);
  }
}
