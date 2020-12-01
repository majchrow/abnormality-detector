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

  displayedColumns: string[] = ['type', 'name', 'event'];

  ngOnInit(): void {
  }

}
