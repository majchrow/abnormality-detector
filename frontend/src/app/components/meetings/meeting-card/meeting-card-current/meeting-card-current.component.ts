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
  @Output() modelEmitter = new EventEmitter<Meeting>();
  @Output() historyEmitter = new EventEmitter<Meeting>();
  @Output() settingEmitter = new EventEmitter<Meeting>();
  @Output() inferenceEmitter = new EventEmitter<Meeting>();

  monitoring: Observable<any>;
  monitored = false;

  constructor() {
  }

  ngOnInit(): void {
  }

  onInferenceClick() {
    this.inferenceEmitter.emit(this.meeting);
  }

  onModelClick() {
    this.modelEmitter.emit(this.meeting);
  }

  onSettingClick() {
    this.settingEmitter.emit(this.meeting);
  }

  onHistoryClick() {
    this.historyEmitter.emit(this.meeting);
  }
}
