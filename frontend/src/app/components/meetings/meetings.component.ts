import {Component, OnInit} from '@angular/core';
import {Meeting} from './class/meeting';
import {MatDialog} from '@angular/material/dialog';
import {ConfirmationDialogService} from '../../services/confirmation-dialog.service';
import {NotificationService} from '../../services/notification.service';
import {MeetingsService} from '../../services/meetings.service';
import {MeetingSSEService} from '../../services/meeting-sse.service';
import {AllMeetings} from './class/all-meetings';
import {NewMeetingDialogComponent} from './new-meeting-dialog/new-meeting-dialog.component';

@Component({
  selector: 'app-meetings',
  templateUrl: './meetings.component.html',
  styleUrls: ['./meetings.component.scss']
})
export class MeetingsComponent implements OnInit {

  constructor(
    private dialog: MatDialog,
    private dialogService: ConfirmationDialogService,
    private notificationService: NotificationService,
    private meetingsService: MeetingsService,
    private meetingSSEService: MeetingSSEService
  ) {
  }

  settingMeeting: Meeting;
  paginatorSize = 1;
  numberOfProductsDisplayedInPage = 24;
  pageSizeOptions = [12, 24];
  allMeetings: AllMeetings;


  updateMeetingsDisplayedInPage(event) {
    console.log(event);
  }

  ngOnInit(): void {
    this.settingMeeting = null;
    this.subscribeRest();
  }

  setting(meeting: Meeting) {
    this.settingMeeting = meeting;
  }


  subscribeRest() {
    this.meetingsService.fetch_meetings().subscribe(
      next => {
        this.allMeetings = next;
        this.subscribeAllSSE();
      },
      error => {
        this.notificationService.warn(error.message);
        this.allMeetings = new AllMeetings(
          [new Meeting('x', [])], [new Meeting('x', [])], [new Meeting('x', [])]
        );
      }
    );
  }

  subscribeAllSSE() {
    this.allMeetings.current.forEach(
      meeting => {
        this.subscribe_sse(meeting.name);
        console.log(`Meeting ${meeting.name} subscribed`);
      }
    );
  }


  subscribe_sse(name: string) {
    this.meetingSSEService.getServerSentEvent(name).subscribe(
      next => {
        this.notificationService.success(
          `Meeting ${name}: ${next.data}`);
      },
      error => {
        if (error.eventPhase !== 2) {
          this.notificationService.warn(error.message);
        }
      }
    );
  }

  delete(meeting: Meeting) {
    this.dialogService.openConfirmDialog('Are you sure you want to delete this meeting?')
      .afterClosed().subscribe(res => {
      if (res) {
        const index: number = this.allMeetings.current.indexOf(meeting);
        if (index !== -1) {
          this.allMeetings.current.splice(index, 1);
          this.notificationService.success('Deleted successfully');
        } else {
          this.notificationService.warn('Failed to delete meeting');
        }
      }
    });
  }

  newMeetingDialog(): void {
    const dialogRef = this.dialog.open(NewMeetingDialogComponent, {
      disableClose: true
    });

    dialogRef.afterClosed().subscribe(() => {
      this.allMeetings = null;
      this.subscribeRest();
    });
  }

}
