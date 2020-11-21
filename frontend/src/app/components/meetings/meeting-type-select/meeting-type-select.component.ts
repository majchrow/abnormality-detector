import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';

interface MeetingType {
  value: string;
  viewValue: string;
}

@Component({
  selector: 'app-meeting-type-select',
  templateUrl: './meeting-type-select.component.html',
  styleUrls: ['./meeting-type-select.component.scss']
})
export class SelectMeetingType {
  @Output() selectedChange = new EventEmitter<string>();

  meetingTypes: MeetingType[] = [
    { value: 'created', viewValue: 'Created' },
    { value: 'current', viewValue: 'Current' },
    { value: 'recent', viewValue: 'Recent' },
    { value: 'all', viewValue: 'All' }
  ];

  onMeetingTypeChange(selectedOption: string) {
    this.selectedChange.emit(selectedOption);
  }
}