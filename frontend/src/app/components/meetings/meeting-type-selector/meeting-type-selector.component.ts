import {Component} from '@angular/core';

interface Meeting {
  value: string;
  viewValue: string;
}

/**
 * @title Basic select
 */
@Component({
  selector: 'app-meeting-type-selector',
  templateUrl: './meeting-type-selector.component.html'
//   styleUrls: ['./meeting-type-selector.component.scss']
})
export class SelectMeetingType {
  meetings: Meeting[] = [
    {value: 'created-0', viewValue: 'Created'},
    {value: 'current-1', viewValue: 'Current'},
    {value: 'recent-2', viewValue: 'Recent'}
  ];
}