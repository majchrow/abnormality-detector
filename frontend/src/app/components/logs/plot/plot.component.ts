import {Component, OnInit} from '@angular/core';
import * as CanvasJS from '../../../../assets/canvasjs.min';

@Component({
  selector: 'app-plot',
  templateUrl: './plot.component.html',
  styleUrls: ['./plot.component.scss']
})
export class PlotComponent implements OnInit {

  constructor() {
  }

  ngOnInit(): void {
    const chart = new CanvasJS.Chart('chartContainer', {
      theme: 'dark2',
      animationEnabled: true,
      exportEnabled: true,
      title: {
        text: 'Logs info'
      },
      data: [{
        type: 'pie',
        showInLegend: true,
        toolTipContent: '<b>{name}</b>: ${y} (#percent%)',
        indexLabel: '{name} - #percent%',
        dataPoints: [
          {y: 1237, name: 'Infos'},
          {y: 441, name: 'Warnings'},
          {y: 312, name: 'Errors'},
          {y: 560, name: 'Successful'}
        ]
      }]
    });

    chart.render();
  }

}
