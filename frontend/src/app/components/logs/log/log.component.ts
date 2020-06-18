import {Component, OnInit} from '@angular/core';
import {Info} from './class/info';

@Component({
  selector: 'app-log',
  templateUrl: './log.component.html',
  styleUrls: ['./log.component.scss']
})
export class LogComponent implements OnInit {

  constructor() {
  }

  latest = 10;
  infos: Array<Info> = [
    new Info('Warning in meeting X',
      '4/1/2021 10:15',
      'warning'
    ),
    new Info('Meeting Y finished successfully',
      '3/1/2021 10:15',
      'success'
    ),
    new Info('Settings successfully changed',
      '2/1/2021 10:15',
      'success'
    ),
    new Info('Reloading meeting Z',
      '1/1/2021 10:15',
      'info'
    ),
    new Info('Wrong date appeared',
      '30/12/2020 10:15',
      'warning'
    ),
  ];

  ngOnInit(): void {
  }

}
