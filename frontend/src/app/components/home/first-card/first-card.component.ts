import {Component, OnInit} from '@angular/core';

@Component({
  selector: 'app-first-card',
  templateUrl: './first-card.component.html',
  styleUrls: ['./first-card.component.scss']
})
export class FirstCardComponent implements OnInit {

  constructor() {
  }

  infos: Array<string> = [
    'Real time notifications',
    'Education rooms observation',
    'Customisable rooms monitoring',
    'Manual conditions model management',
    'ML model training on historical data',
    'Models evaluation on historical data',
    'Anomaly history review',
    'Report generation per meeting or room'
  ];

  ngOnInit(): void {
  }

}
