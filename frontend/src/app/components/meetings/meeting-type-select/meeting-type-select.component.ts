import {Component, EventEmitter, Input, Output} from '@angular/core';

interface MeetingType {
  value: string;
  viewValue: string;
}

@Component({
  selector: 'app-meeting-type-select',
  templateUrl: './meeting-type-select.component.html',
  styleUrls: ['./meeting-type-select.component.scss']
})
export class SelectMeetingTypeComponent {
  @Output() selectedChange = new EventEmitter<string>();
  @Input() selected: string;

  meetingTypes: MeetingType[] = [
    {value: 'created', viewValue: 'Created'},
    {value: 'current', viewValue: 'Current'},
    {value: 'recent', viewValue: 'Recent'},
  ];

  onMeetingTypeChange(selectedOption: string) {
    this.selectedChange.emit(selectedOption);
  }
}
