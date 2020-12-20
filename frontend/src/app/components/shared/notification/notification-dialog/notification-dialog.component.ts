import {Component, Inject, OnInit} from '@angular/core';
import {ConfirmationDialogService} from '../../../../services/confirmation-dialog.service';
import {MAT_DIALOG_DATA, MatDialogRef} from '@angular/material/dialog';

@Component({
  selector: 'app-notification-dialog',
  templateUrl: './notification-dialog.component.html',
  styleUrls: ['./notification-dialog.component.scss']
})
export class NotificationDialogComponent implements OnInit {

  constructor(
    @Inject(MAT_DIALOG_DATA) public data: any[]
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

  displayedColumns: string[] = ['type', 'date', 'name', 'event'];

  ngOnInit(): void {
  }

}
