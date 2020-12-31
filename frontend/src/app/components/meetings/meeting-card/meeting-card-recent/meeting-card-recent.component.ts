import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Meeting} from '../../class/meeting';

@Component({
  selector: 'app-meeting-card-recent',
  templateUrl: './meeting-card-recent.component.html',
  styleUrls: ['./meeting-card-recent.component.scss']
})
export class MeetingCardRecentComponent implements OnInit {

  @Input() meeting: Meeting;
  @Output() modelEmitter = new EventEmitter<Meeting>();
  @Output() historyEmitter = new EventEmitter<Meeting>();
  @Output() settingEmitter = new EventEmitter<Meeting>();
  @Output() inferenceEmitter = new EventEmitter<Meeting>();

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

