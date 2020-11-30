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

  selected: string;
  settingMeeting: Meeting;
  historyMeeting: Meeting;
  paginatorSize = 1;
  numberOfProductsDisplayedInPage = 24;
  pageSizeOptions = [12, 24];
  allMeetings: AllMeetings;
  selectedMeetings: AllMeetings;
  meetingType = 'current';


  updateMeetingsDisplayedInPage(event) {
    console.log(event);
  }

  ngOnInit(): void {
    this.initAllMeetings();
    this.subscribeRest();
  }

  initAllMeetings() {
    this.selected = 'None';
    this.initHistoryMeeting();
    this.initSettingMeeting();
  }

  initSettingMeeting() {
    this.settingMeeting = null;
  }

  initHistoryMeeting() {
    this.historyMeeting = null;
  }

  onSettingClick(meeting: Meeting) {
    this.settingMeeting = meeting;
    this.selected = 'setting';
  }

  onHistoryClick(meeting: Meeting) {
    this.historyMeeting = meeting;
    this.selected = 'history';
  }


  subscribeRest() {
    this.meetingsService.fetchMeetings().subscribe(
      next => {
        this.allMeetings = next;
        this.filterMeetings();
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

  changeMeetingType(selected: string) {
    this.meetingType = selected;
    this.filterMeetings();
  }

  filterMeetings() {
    switch (this.meetingType) {
      case 'created': {
        this.selectedMeetings = new AllMeetings([], [], [...this.allMeetings.created]);
        break;
      }
      case 'current': {
        this.selectedMeetings = new AllMeetings([...this.allMeetings.current], [], []);
        break;
      }
      case 'recent': {
        this.selectedMeetings = new AllMeetings([], [...this.allMeetings.recent], []);
        break;
      }
      default: {
        this.selectedMeetings = new AllMeetings([...this.allMeetings.current], [...this.allMeetings.recent], [...this.allMeetings.created]);
      }
    }
  }

  subscribeAllSSE() {
    // this.allMeetings.current.forEach(
    //   meeting => {
    //     this.subscribe_sse(meeting.name);
    //     console.log(`Meeting ${meeting.name} subscribed`);
    //   }
    // );
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

  onDeleteClick(meeting: Meeting) {
    this.dialogService.openConfirmDialog('Are you sure you want to delete this meeting?')
      .afterClosed().subscribe(res => {
      if (res) {
        this.meetingsService.deleteMeeting(meeting).subscribe(
          () => {
            this.notificationService.success('Deleted successfully');
            this.allMeetings = null;
            this.subscribeRest();
          }, () => {
            this.notificationService.warn('Failed to delete meeting');
          }
        );
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
