import {Component, OnInit} from '@angular/core';
import {Meeting} from './class/meeting';
import {MatDialog} from '@angular/material/dialog';
import {ConfirmationDialogService} from '../../services/confirmation-dialog.service';
import {NotificationService} from '../../services/notification.service';

@Component({
  selector: 'app-meetings',
  templateUrl: './meetings.component.html',
  styleUrls: ['./meetings.component.scss']
})
export class MeetingsComponent implements OnInit {

  constructor(
    private dialog: MatDialog,
    private dialogService: ConfirmationDialogService,
    private notificationService: NotificationService
  ) {
  }


  paginatorSize = 1;
  numberOfProductsDisplayedInPage = 24;
  pageSizeOptions = [12, 24];
  meetings: Array<Meeting> = [
    new Meeting('Meeting 1', ['chemia', '29 osob']),
    new Meeting('Meeting 2', ['biologia', '3 osoby']),
    new Meeting('Meeting 3', ['matematyka', '5 osoby']),
    new Meeting('Meeting 4', ['informatyka', '1 osoba'])
  ];

  updateMeetingsDisplayedInPage(event) {
    console.log(event);
  }

  ngOnInit(): void {
  }

  delete(meeting: Meeting) {
    this.dialogService.openConfirmDialog('Are you sure you want to delete this meeting?')
      .afterClosed().subscribe(res => {
      if (res) {
        const index: number = this.meetings.indexOf(meeting);
        if (index !== -1) {
          this.meetings.splice(index, 1);
          this.notificationService.success('Deleted successfully');
        } else {
          this.notificationService.warn('Failed to delete meeting');
        }
      }
    });
  }

  addMeeting() {
    this.meetings.push(
      new Meeting('Meeting X', ['Unknown'])
    );
  }
}
